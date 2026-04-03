#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# version 7.62
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

import argparse
import logging
import os
import socket
import threading
import time

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
# TSL2591 sensor loop
# ---------------------------------------------------------------------------

def _run_tsl2591():
    """Read TSL2591 and serve raw lux. No smoothing — that is the caller's job."""
    from python_tsl2591 import tsl2591

    INTEGRATION_TIME_VAL     = 0x01    # 200 ms integration time
    INTEGRATION_TIME_SECONDS = 0.22    # 200 ms + 20 ms safety buffer
    GAIN_VAL                 = 0x10    # Medium gain
    HYSTERESIS               = 0.05    # minimum lux change to update output

    sensor   = None
    last_lux = -1.0

    while True:
        try:
            if sensor is None:
                sensor = tsl2591()
                sensor.set_timing(INTEGRATION_TIME_VAL)
                sensor.set_gain(GAIN_VAL)
                last_lux = -1.0
                logging.info("TSL2591 initialised")

            sensor.enable()
            time.sleep(INTEGRATION_TIME_SECONDS)    # wait for a fresh integration cycle

            full, ir = sensor.get_full_luminosity()
            raw_lux  = sensor.calculate_lux(full, ir)

            # Only update output if change exceeds hysteresis threshold
            if last_lux < 0 or abs(raw_lux - last_lux) > HYSTERESIS:
                last_lux = raw_lux
                _set_lux(last_lux)

        except Exception as e:
            logging.error(f"TSL2591 read failed: {e}")
            _set_lux(-1.0)
            sensor   = None    # force re-init on next cycle
            last_lux = -1.0


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
