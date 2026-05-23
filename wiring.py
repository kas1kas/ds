# -*- coding: utf-8 -*-
__version__ = "8.00"
# wiring.py — LED strip wiring layouts for the Woordklok
#
# Translates logical coordinates to physical LED strip indices.
# All hardware geometry lives here — wk.py has no wiring arithmetic.
#
# ONE coordinate convention everywhere (spec section 7):
#
#   x = 0-based, 0 = leftmost column  (front view)
#   y = 0-based, 0 = TOP row          (y=0=top throughout)
#
# Two methods, same convention:
#
#   wiring.word_xy(x, y)     Word grid:  x=0..10, y=0..9
#   wiring.panel_xy(x, y)    Full panel: x=0..W-1, y=0..H-1
#
# Callers pass 0-based coordinates.
# 1-based word-indices from config_gen.json are converted to 0-based
# at the call site in wk.py  (index - 1 before calling word_xy).
#
# Minute dot physical indices live in config_loc.json MINUTE_DOTS,
# keyed MD1..MD4. wiring.py does not store or compute them.
#
# How to add a new hardware variant:
#   1. Define _word_xy_<name>(x, y) -> int   (0-based, y=0=top)
#   2. Define _panel_xy_<name>(x, y) -> int  (0-based, y=0=top)
#   3. Add entries to _WORD_BUILDERS, _PANEL_BUILDERS, PANEL_DIMS.
#   4. Add MINUTE_DOTS entry to config_loc.json.
#   5. Add entry to _HARDWARE_PROFILES in wk.py.

import logging

log = logging.getLogger(__name__)

_WORD_ROWS = 10
_WORD_COLS = 11


# ---------------------------------------------------------------------------
# VERTICAL wiring  (hardware: "11x10V")
#
# Verified against spec-11X10Vscreenshot.png (front view).
#
# Strips run vertically, 11 columns, serpentine left→right (front view).
# Even columns (x=0,2,4,6,8,10): top→bottom  (index increases with y)
# Odd  columns (x=1,3,5,7,9):    bottom→top  (index decreases with y)
#
# Physical index layout (0-based):
#   0        = MD2  (bottom-right, front view)
#   1        = MD1  (top-right,    front view)
#   2..111   = word area — col 11 (x=10) first, col 1 (x=0) last
#   112      = MD3  (bottom-left,  front view)
#   113      = MD4  (top-left,     front view)
#
# Derived base addresses (0-based):
#   Even x: base = 102 - (x//2)*20  → led = base + y
#   Odd  x: base = 101 - (x//2)*20  → led = base - y
# ---------------------------------------------------------------------------

def _word_xy_vertical(x: int, y: int) -> int:
    if x % 2 == 0:
        return 102 - (x // 2) * 20 + y
    else:
        return 101 - (x // 2) * 20 - y


def _panel_xy_vertical(x: int, y: int) -> int:
    """11x10V panel == word grid."""
    return _word_xy_vertical(x, y)


# ---------------------------------------------------------------------------
# HORIZONTAL wiring  (hardware: "11x10H")
#
# Verified against spec-11X10Hscreenshot.png (front view).
#
# Strips run horizontally, 10 rows, data connector top-right (front view).
# Even rows (y=0,2,4,6,8): left→right
# Odd  rows (y=1,3,5,7,9): right→left
#
# Physical index layout (0-based):
#   0        = MD2  (bottom-right, front view)
#   1..11    = row y=9 (bottom), right→left
#   12       = MD3  (bottom-left, front view)
#   13..23   = row y=8,  left→right
#   24..34   = row y=7,  right→left
#   35..45   = row y=6,  left→right
#   46..56   = row y=5,  right→left
#   57..67   = row y=4,  left→right
#   68..78   = row y=3,  right→left
#   79..89   = row y=2,  left→right
#   90..100  = row y=1,  right→left
#   101      = MD4  (top-left, front view)
#   102..112 = row y=0 (top), left→right
#   113      = MD1  (top-right, front view)
#
# Base (0-based) = leftmost LED index for each row:
# ---------------------------------------------------------------------------

_H_STRIP_BASE = [
    102,   # y=0  top     left→right   leds 102..112  (MD1=113 after)
     90,   # y=1          right→left   leds 90..100   (MD4=101 after)
     79,   # y=2          left→right   leds 79..89
     68,   # y=3          right→left   leds 68..78
     57,   # y=4          left→right   leds 57..67
     46,   # y=5          right→left   leds 46..56
     35,   # y=6          left→right   leds 35..45
     24,   # y=7          right→left   leds 24..34
     13,   # y=8          left→right   leds 13..23
      1,   # y=9  bottom  right→left   leds 1..11     (MD2=0 before, MD3=12 after)
]


def _word_xy_horizontal(x: int, y: int) -> int:
    base = _H_STRIP_BASE[y]
    if y % 2 == 0:
        return base + x
    else:
        return base + (_WORD_COLS - 1 - x)


def _panel_xy_horizontal(x: int, y: int) -> int:
    """11x10H panel == word grid."""
    return _word_xy_horizontal(x, y)


# ---------------------------------------------------------------------------
# MATRIX16 wiring  (hardware: "16x16V")
#
# Verified against spec-16X16Vscreenshot.png (front view).
#
# 16×16 LED panel, column-serpentine.
# Data connector: bottom-right corner (front view).
# Col 16 (x=15, rightmost): bottom→top  (LED 0 at bottom)
# Col 15 (x=14):            top→bottom
# Alternating: col_from_right even → bottom→top, odd → top→bottom
#
# col_from_right = 15 - x
# Even col_from_right: led = col_from_right*16 + (15-y)   (bottom→top → y=0=top)
# Odd  col_from_right: led = col_from_right*16 + y
#
# Word grid sits at panel offset col=3, row=3 (0-based).
# word(x, y) → panel(x+3, y+3)
# ---------------------------------------------------------------------------

_PANEL16_SIZE    = 16
_WORD_OFFSET_COL = 3
_WORD_OFFSET_ROW = 3


def _panel_xy_matrix16(x: int, y: int) -> int:
    cfr = _PANEL16_SIZE - 1 - x          # col_from_right, 0-based
    base = cfr * _PANEL16_SIZE
    return base + (_PANEL16_SIZE - 1 - y) if cfr % 2 == 0 else base + y


def _word_xy_matrix16(x: int, y: int) -> int:
    return _panel_xy_matrix16(x + _WORD_OFFSET_COL, y + _WORD_OFFSET_ROW)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_WORD_BUILDERS = {
    "vertical":   _word_xy_vertical,
    "horizontal": _word_xy_horizontal,
    "matrix16":   _word_xy_matrix16,
}

_PANEL_BUILDERS = {
    "vertical":   _panel_xy_vertical,
    "horizontal": _panel_xy_horizontal,
    "matrix16":   _panel_xy_matrix16,
}

# Physical panel dimensions (cols, rows) — used by effects
PANEL_DIMS = {
    "vertical":   (11, 10),
    "horizontal": (11, 10),
    "matrix16":   (16, 16),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Wiring:
    """
    Translates logical clock coordinates to physical LED strip indices.

    Instantiated by wk.py with the internal wiring name derived from HARDWARE:
        wiring = Wiring("vertical" | "horizontal" | "matrix16")

    All inputs are 0-based with y=0=TOP (spec section 7):
        x = 0-based, 0 = leftmost column (front view)
        y = 0-based, 0 = top row

    Methods:
        word_xy(x, y)     x=0..10,  y=0..9   → physical led index (0-based)
        panel_xy(x, y)    x=0..W-1, y=0..H-1 → physical led index (0-based)
        panel_dims         (cols, rows) of the full physical panel
    """

    def __init__(self, name: str):
        if name not in _WORD_BUILDERS:
            known = ", ".join(sorted(_WORD_BUILDERS))
            log.warning(
                "Unknown wiring '%s', falling back to 'vertical'. Known: %s",
                name, known
            )
            name = "vertical"
        self.name       = name
        self._word_fn   = _WORD_BUILDERS[name]
        self._panel_fn  = _PANEL_BUILDERS[name]
        self.panel_dims = PANEL_DIMS[name]
        log.info("Wiring: %s  panel=%s", name, self.panel_dims)

    def word_xy(self, x: int, y: int) -> int:
        """
        Physical LED index for word grid position.
        x=0..10 left→right, y=0..9 top→bottom (y=0=TOP).
        Returns 0-based physical index.
        """
        return self._word_fn(x, y)

    def panel_xy(self, x: int, y: int) -> int:
        """
        Physical LED index for full panel position.
        x=0..cols-1 left→right, y=0..rows-1 top→bottom (y=0=TOP).
        Returns 0-based physical index.
        """
        return self._panel_fn(x, y)
