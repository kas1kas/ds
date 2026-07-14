#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = "1.4"
# 1.4: send 4 digits in: conn.sendall(f"{lux:.4f}\n".encode())
# 1.3: HYSTERESIS = 0.005  # ~1 ADC count at HIGH gain; smoothing handled by caller
# lux_daemon.py  –  Reads the TSL2591 light sensor and serves the raw lux
#                   value over a Unix domain socket at SOCKET_PATH.
#
# Any client that connects receives the current lux as a UTF-8 string, e.g.:
#     "0.18\n"
# or "-1.00\n" when the sensor is unavailable.
#
# Smoothing and EMA are intentionally NOT done here.
# The caller (wk.py or any other client) is responsible for smoothing.
#
# Run manually or via systemd:
#     python3 lux_daemon.py --sensor TSL2591
#
# FIX (v7.65 / __version__ 1.1): replaced python-tsl2591 library with direct
# smbus2 calls. The python-tsl2591 library opens a new smbus.SMBus fd in
# __init__ and never closes it, causing fd exhaustion (~1000 open
# /dev/i2c-1 handles) over time as the sensor object is recreated on each
# error recovery cycle. smbus2.SMBus is opened ONCE at startup and kept
# open for the lifetime of the process — no fd leak possible.
#
# FEATURE (__version__ 1.2): auto-ranging gain. We care about precision in
# the 0-1 lux range and don't care about detail above ~100 lux (the LUT
# clamps to max brightness there anyway). So we run at GAIN_HIGH (428x) by
# default for fine low-light resolution, and only step down to GAIN_MED /
# GAIN_LOW when the raw channel reading approaches saturation. We step back
# up to HIGH once light drops again so we regain precision near zero.
# Integration time (200ms) is unaffected by gain and stays constant, so
# polling cadence does not change. The persistent smbus2 handle from the
# fd-leak fix is untouched by gain switches — only the CONTROL register is
# rewritten.

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

# Integration time: 0x01 = 200 ms (unaffected by gain — stays fixed)
_INTEGRATION_TIME        = 0x01
_INTEGRATION_SECONDS     = 0.22   # 200 ms + 20 ms safety buffer

# Gain register values
_GAIN_LOW                = 0x00   # 1x     (bright light)
_GAIN_MED                = 0x10   # 25x    (general purpose)
_GAIN_HIGH               = 0x20   # 428x   (low light)
_GAIN_MAX                = 0x30   # 9876x  (extreme low light, unused here)

# Gain ladder, low-light-first: (register value, multiplier)
_GAIN_LADDER = [
    (_GAIN_HIGH, 428),
    (_GAIN_MED,  25),
    (_GAIN_LOW,  1),
]

# Raw channel0 is a 16-bit value (max 0xFFFF = 65535). The datasheet
# recommends staying well clear of full-scale to avoid non-linearity, so we
# treat anything >= SAT_THRESHOLD as saturated for our purposes.
_SAT_THRESHOLD   = 36000
# When stepping back up to a more sensitive gain, only do so if the raw
# count *at that higher gain* would still land safely below threshold (with
# margin), to avoid flapping back and forth at the boundary.
_HEADROOM_FACTOR = 0.7

# Lux formula coefficients (from AMS datasheet / python-tsl2591 source)
_LUX_DF                  = 408.0
_LUX_COEFB               = 1.64
_LUX_COEFC               = 0.59
_LUX_COEFD               = 0.86

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


def _set_gain(bus, gain_reg):
    """Write integration time + gain together, as the CONTROL register packs both."""
    _write(bus, _TSL2591_REGISTER_CONTROL, _INTEGRATION_TIME | gain_reg)


def _calculate_lux(full, ir, gain_mult, atime_ms):
    """
    Calculate lux from raw channel values using the AMS datasheet formula.
    Returns -1.0 on overflow or invalid input.
    """
    if full == 0xFFFF or ir == 0xFFFF:
        return -1.0   # sensor saturated

    cpl = (atime_ms * gain_mult) / _LUX_DF
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

    Auto-ranging gain: stay at GAIN_HIGH for low-light precision, drop to
    GAIN_MED/GAIN_LOW on saturation, climb back to GAIN_HIGH once the raw
    count comfortably allows it.
    """
    HYSTERESIS = 0.005    # ~1 ADC count at HIGH gain; smoothing handled by caller
    atime_ms   = _ATIME_MULTIPLIERS[_INTEGRATION_TIME]

    bus         = None
    last_lux    = -1.0
    initialized = False
    gain_index  = 0    # start at GAIN_HIGH

    while True:
        try:
            gain_reg, gain_mult = _GAIN_LADDER[gain_index]

            # Open bus once — keep it open forever
            if bus is None:
                bus = smbus2.SMBus(1)
                logging.info("smbus2 bus opened")
                initialized = False

            if not initialized:
                _set_gain(bus, gain_reg)
                _disable(bus)
                logging.info(f"TSL2591 initialised (smbus2 direct), gain index {gain_index}")
                initialized = True
                last_lux = -1.0

            _enable(bus)
            time.sleep(_INTEGRATION_SECONDS)    # wait for a fresh integration cycle

            full = _read_word(bus, _TSL2591_REGISTER_CHAN0)
            ir   = _read_word(bus, _TSL2591_REGISTER_CHAN1)
            _disable(bus)

            # --- Saturation check (step DOWN to a less sensitive gain) ---
            if (full >= _SAT_THRESHOLD or full == 0xFFFF) and gain_index < len(_GAIN_LADDER) - 1:
                gain_index += 1
                next_gain_reg = _GAIN_LADDER[gain_index][0]
                _set_gain(bus, next_gain_reg)
                logging.info(
                    f"Channel saturated (full={full}) — stepping down to "
                    f"gain index {gain_index}"
                )
                continue    # re-read immediately at the new gain, no lux update

            raw_lux = _calculate_lux(full, ir, gain_mult, atime_ms)
            if raw_lux < 0:
                logging.warning("TSL2591 saturation — skipping frame")
                continue

            # --- Headroom check (step UP to a more sensitive gain) -------
            if gain_index > 0:
                higher_mult = _GAIN_LADDER[gain_index - 1][1]
                projected_full = full * (higher_mult / gain_mult)
                if projected_full < _SAT_THRESHOLD * _HEADROOM_FACTOR:
                    gain_index -= 1
                    next_gain_reg = _GAIN_LADDER[gain_index][0]
                    _set_gain(bus, next_gain_reg)
                    logging.info(
                        f"Light low enough (full={full}) — stepping up to "
                        f"gain index {gain_index}"
                    )
                    continue    # re-read immediately at the new gain

            if last_lux < 0 or abs(raw_lux - last_lux) > HYSTERESIS:
                last_lux = raw_lux
                _set_lux(last_lux)

        except Exception as e:
            logging.error(f"TSL2591 read failed: {e}")
            _set_lux(-1.0)
            last_lux    = -1.0
            initialized = False
            gain_index  = 0       # restart auto-ranging from GAIN_HIGH
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
        conn.sendall(f"{lux:.4f}\n".encode())
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
