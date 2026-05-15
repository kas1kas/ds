# -*- coding: utf-8 -*-
__version__ = "1.0"
# lux_client.py  –  Reads the current lux value from lux_daemon.
#
# Usage:
#     from lux_client import get_lux
#
#     lux = get_lux()   # float >= 0, or -1.0 if daemon/sensor unavailable

import socket

SOCKET_PATH = "/tmp/lux.sock"
TIMEOUT     = 0.5               # keep short; callers must never block long


def get_lux() -> float:
    """Return current raw lux from the daemon, or -1.0 on any failure."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect(SOCKET_PATH)
            data = s.recv(64).decode().strip()
            return float(data)
    except Exception:
        return -1.0
