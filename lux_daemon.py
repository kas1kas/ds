#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# version 7.71
# lux_daemon.py  –  Reads the TSL2591 light sensor and serves the raw lux
#                   value over a Unix domain socket at SOCKET_PATH.
#
# Any client that connects receives the current lux as a UTF-8 string, e.g.:
#     "42.70\n"
# or "-1.00\n" when the sensor is unavailable.
#
# Smoothing and EMA are intentionally NOT done here.
# The caller (wk.py or any other client) is responsible for smoothing.
#
# Run manually or via systemd:
#     python3 lux_daemon.py --sensor TSL2591
#
# FIX (v7.65): replaced python-tsl2591 library with direct smbus2 calls.
# The python-tsl2591 library opens a new smbus.SMBus fd in __init__ and
# never closes it, causing fd exhaustion (~1000 open /dev/i2c-1 handles)
# over time as the sensor object is recreated on each error recovery cycle.
# smbus2.SMBus is opened ONCE at startup and kept open for the lifetime of
# the process — no fd leak possible.

import argparse
import logging
import os
import socket
import threading
import time

import smbus2

SOCKET_PATH = "/tmp/lux.sock"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [lux_daemon] %(levelname)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Shared lux state  (written by sensor thread, read by socket server)
# ---------------------------------------------------------------------------
_lux_lock    = threading.Lock()
_current_lux = -1.0


def _set_lux(value: float):
    global _current_lux
    with _lux_lock:
        _current_lux = value


def _get_lux() -> float:
    with _lux_lock:
        return _current_lux


# ---------------------------------------------------------------------------
# TSL2591 register map and constants
# ---------------------------------------------------------------------------

_TSL2591_ADDR            = 0x29
_TSL2591_COMMAND_BIT     = 0xA0   # bits 7 and 5 for 'command normal'
_TSL2591_REGISTER_ENABLE = 0x00
_TSL2591_REGISTER_CONTROL= 0x01
_TSL2591_REGISTER_CHAN0  = 0x14   # ALS data channel 0 low byte (word read)
_TSL2591_REGISTER_CHAN1  = 0x16   # ALS data channel 1 low byte (word read)

_TSL2591_ENABLE_POWERON  = 0x01
_TSL2591_ENABLE_AEN      = 0x02   # ALS enable
_TSL2591_ENABLE_POWEROFF = 0x00

# Integration time: 0x01 = 200 ms
_INTEGRATION_TIME        = 0x01
_INTEGRATION_SECONDS     = 0.22   # 200 ms + 20 ms safety buffer

# Gain: 0x10 = medium (25x)
_GAIN                    = 0x10

# Lux formula coefficients (from AMS datasheet / python-tsl2591 source)
_LUX_DF                  = 408.0
_LUX_COEFB               = 1.64
_LUX_COEFC               = 0.59
_LUX_COEFD               = 0.86

# Gain multipliers for lux calculation
_GAIN_MULTIPLIERS = {
    0x00: 1,    # low   (1x)
    0x10: 25,   # medium (25x)
    0x20: 428,  # high  (428x)
    0x30: 9876, # max   (9876x)
}

# Integration time multipliers (atime) for lux calculation
_ATIME_MULTIPLIERS = {
    0x00: 100,  # 100 ms
    0x01: 200,  # 200 ms
    0x02: 300,  # 300 ms
    0x03: 400,  # 400 ms
    0x04: 500,  # 500 ms
    0x05: 600,  # 600 ms
}


def _write(bus, register, value):
    bus.write_byte_data(_TSL2591_ADDR, _TSL2591_COMMAND_BIT | register, value)


def _read_word(bus, register):
    return bus.read_word_data(_TSL2591_ADDR, _TSL2591_COMMAND_BIT | register)


def _enable(bus):
    _write(bus, _TSL2591_REGISTER_ENABLE, _TSL2591_ENABLE_POWERON | _TSL2591_ENABLE_AEN)


def _disable(bus):
    _write(bus, _TSL2591_REGISTER_ENABLE, _TSL2591_ENABLE_POWEROFF)


def _calculate_lux(full, ir, gain, atime_ms):
    """
    Calculate lux from raw channel values using the AMS datasheet formula.
    Returns -1.0 on overflow or invalid input.
    """
    if full == 0xFFFF or ir == 0xFFFF:
        return -1.0   # sensor saturated

    gain_mult  = _GAIN_MULTIPLIERS.get(gain, 25)
    atime_mult = atime_ms

    cpl = (atime_mult * gain_mult) / _LUX_DF
    if cpl == 0:
        return -1.0

    lux1 = (full - (_LUX_COEFB * ir)) / cpl
    lux2 = ((_LUX_COEFC * full) - (_LUX_COEFD * ir)) / cpl
    lux  = max(lux1, lux2)
    return max(0.0, lux)


# ---------------------------------------------------------------------------
# TSL2591 sensor loop — one persistent smbus2 handle, never recreated
# ---------------------------------------------------------------------------

def _run_tsl2591():
    """
    Read TSL2591 using smbus2 directly.

    A single SMBus handle is opened at startup and held open for the lifetime
    of the process.  On I2C errors the sensor registers are re-initialised
    but the bus handle is never closed and reopened, eliminating the fd leak
    that occurred with the python-tsl2591 library.
    """
    HYSTERESIS = 0.05   # minimum lux change to update shared state
    atime_ms   = _ATIME_MULTIPLIERS[_INTEGRATION_TIME]

    bus      = None
    last_lux = -1.0
    initialized = False

    while True:
        try:
            # Open bus once — keep it open forever
            if bus is None:
                bus = smbus2.SMBus(1)
                logging.info("smbus2 bus opened")
                initialized = False

            if not initialized:
                _write(bus, _TSL2591_REGISTER_CONTROL, _INTEGRATION_TIME | _GAIN)
                _disable(bus)
                logging.info("TSL2591 initialised (smbus2 direct)")
                initialized = True
                last_lux = -1.0

            _enable(bus)
            time.sleep(_INTEGRATION_SECONDS)    # wait for a fresh integration cycle

            full = _read_word(bus, _TSL2591_REGISTER_CHAN0)
            ir   = _read_word(bus, _TSL2591_REGISTER_CHAN1)
            _disable(bus)

            raw_lux = _calculate_lux(full, ir, _GAIN, atime_ms)
            if raw_lux < 0:
                logging.warning("TSL2591 saturation — skipping frame")
                continue

            if last_lux < 0 or abs(raw_lux - last_lux) > HYSTERESIS:
                last_lux = raw_lux
                _set_lux(last_lux)

        except Exception as e:
            logging.error(f"TSL2591 read failed: {e}")
            _set_lux(-1.0)
            last_lux    = -1.0
            initialized = False
            # Do NOT close/reopen the bus — just re-init the sensor registers
            # on the next cycle.  Only reopen if the bus itself is gone.
            if bus is not None:
                try:
                    bus.read_byte(_TSL2591_ADDR)   # probe — if this raises, bus is dead
                except Exception:
                    logging.warning("Bus probe failed — reopening smbus2")
                    try:
                        bus.close()
                    except Exception:
                        pass
                    bus = None
            time.sleep(1.0)   # back-off before retry


SENSOR_LOOPS = {
    "TSL2591": _run_tsl2591,
}


# ---------------------------------------------------------------------------
# Unix socket server
# ---------------------------------------------------------------------------

def _handle_client(conn: socket.socket):
    try:
        lux = _get_lux()
        conn.sendall(f"{lux:.2f}\n".encode())
    except Exception as e:
        logging.warning(f"Client send failed: {e}")
    finally:
        conn.close()


def _run_server():
    if os.path.exists(SOCKET_PATH):
        try:
            os.unlink(SOCKET_PATH)
        except PermissionError:
            logging.error(
                f"Cannot remove {SOCKET_PATH} — owned by another user. "
                f"Run: sudo rm {SOCKET_PATH}"
            )
            raise

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.bind(SOCKET_PATH)
        srv.listen(8)
        os.chmod(SOCKET_PATH, 0o660)
        logging.info(f"Listening on {SOCKET_PATH}")

        while True:
            try:
                conn, _ = srv.accept()
                t = threading.Thread(target=_handle_client, args=(conn,), daemon=True)
                t.start()
            except Exception as e:
                logging.error(f"Accept error: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Light sensor lux daemon")
    parser.add_argument(
        "--sensor",
        choices=list(SENSOR_LOOPS.keys()),
        required=True,
        help="Sensor type to use",
    )
    args = parser.parse_args()

    t = threading.Thread(target=SENSOR_LOOPS[args.sensor], daemon=True)
    t.start()
    logging.info(f"Sensor thread started for {args.sensor}")

    _run_server()   # blocks forever


if __name__ == "__main__":
    main()
