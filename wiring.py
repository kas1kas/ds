# -*- coding: utf-8 -*-
__version__ = "7.85"
# wiring.py — LED strip wiring layouts for the Woordklok
#
# Translates logical coordinates to physical LED strip indices.
# All hardware geometry lives here — wk.py has no wiring arithmetic.
#
# Two coordinate spaces, two methods:
#
#   wiring.word_xy(x, y)
#     Word grid: x=0..10 left→right, y=0..9 bottom→top.
#     Used for clock words, cls(), and setcolor_x_y(effect_full_panel=False).
#
#   wiring.panel_xy(x, y)
#     Panel: x=0..W-1 left→right, y=0..H-1 top→bottom (screen-natural).
#     Used by effects for full-panel rendering (setcolor_x_y(effect_full_panel=True)).
#
# Minute dot physical indices are stored in config_gen.json MINUTE_DOTS,
# keyed by hardware name ("11x10V", "11x10H", "16x16").
# wiring.py does not store them.
#
# How to add a new hardware variant:
#   1. Define _word_xy_<name>(x, y) -> int
#   2. Define _panel_xy_<name>(x, y) -> int
#   3. Add entry to _WORD_BUILDERS, _PANEL_BUILDERS, PANEL_DIMS.
#   4. Add entry to config_gen.json MINUTE_DOTS.
#   5. Add entry to _HARDWARE_PROFILES in wk.py.

import logging

log = logging.getLogger(__name__)

_WORD_ROWS = 10
_WORD_COLS = 11


# ---------------------------------------------------------------------------
# VERTICAL wiring  (hardware: "11x10V")
# Column-strip serpentine, strips run vertically, columns snake left→right.
# Even columns (x=0,2,...): bottom→top.
# Odd  columns (x=1,3,...): top→bottom.
#
# Physical indices:
#   0, 1       = minute dots ML2, ML1
#   2 .. 111   = word area (110 LEDs)
#   112, 113   = minute dots ML3, ML4
# ---------------------------------------------------------------------------

def _word_xy_vertical(x, y):
    if x % 2 == 0:
        return 2 + x * _WORD_ROWS + y
    else:
        return 2 + x * _WORD_ROWS + (_WORD_ROWS - 1 - y)

def _panel_xy_vertical(x, y):
    """Panel space: y=0 is TOP. Flip y to map to word_xy."""
    #return _word_xy_vertical(x, _WORD_ROWS - 1 - y)
    return _word_xy_vertical(x, y)

# ---------------------------------------------------------------------------
# HORIZONTAL wiring  (hardware: "11x10H")
# Row-strip serpentine, strips run horizontally, rows snake top→bottom.
# Even strip rows (strip_row=0,2,...): left→right.
# Odd  strip rows (strip_row=1,3,...): right→left.
# strip_row=0 is the TOP row (y=9 in word coords).
#
# Physical layout:
#   0          = ML1  minute dot  (before top row)
#   1  ..  11  = row 9  top     L→R
#   12         = ML2  minute dot  (after top row)
#   13 ..  23  = row 8           R→L
#   24 ..  34  = row 7           L→R
#   35 ..  45  = row 6           R→L
#   46 ..  56  = row 5           L→R
#   57 ..  67  = row 4           R→L
#   68 ..  78  = row 3           L→R
#   79 ..  89  = row 2           R→L
#   90 .. 100  = row 1           L→R
#   101        = ML3  minute dot  (after row 1, before bottom row)
#   102 .. 112 = row 0  bottom  R→L
#   113        = ML4  minute dot  (after bottom row)
# ---------------------------------------------------------------------------

def _word_xy_horizontal(x, y):
    """Word coords: y=0=bottom, y=9=top."""
    strip_row = 9 - y          # y=9→strip_row=0 (top), y=0→strip_row=9 (bottom)
    return _horizontal_phys(x, strip_row)

def _panel_xy_horizontal(x, y):
    """Panel coords: y=0=top. strip_row == y directly."""
    return _horizontal_phys(x, y)

def _horizontal_phys(x, strip_row):
    """Common formula for horizontal wiring given strip_row (0=top)."""
    if strip_row == 0:
        return 1 + x
    elif 1 <= strip_row <= 7:
        base = 13 + (strip_row - 1) * _WORD_COLS
        return base + x if strip_row % 2 == 0 else base + (_WORD_COLS - 1 - x)
    elif strip_row == 8:
        return 90 + x
    elif strip_row == 9:
        return 102 + (_WORD_COLS - 1 - x)
    else:
        raise ValueError(f"strip_row={strip_row} out of range 0..9")


# ---------------------------------------------------------------------------
# MATRIX16 wiring  (hardware: "16x16")
# 16×16 LED panel, column-serpentine.
# Word grid sits at panel offset col+2, row+3.
# Even panel columns: led = panel_x*16 + (15 - panel_y)
# Odd  panel columns: led = panel_x*16 + panel_y
# ---------------------------------------------------------------------------

_PANEL16_COLS    = 16
_PANEL16_ROWS    = 16
_WORD_OFFSET_COL = 2
_WORD_OFFSET_ROW = 3

def _word_xy_matrix16(x, y):
    """Word coords: y=0=bottom → panel_y = y + 3."""
    panel_x = x + _WORD_OFFSET_COL
    panel_y = y + _WORD_OFFSET_ROW
    if panel_x % 2 == 0:
        return panel_x * _PANEL16_COLS + (_PANEL16_COLS - 1 - panel_y)
    else:
        return panel_x * _PANEL16_COLS + panel_y

def _panel_xy_matrix16(x, y):
    """
    16x16 panel, full-panel coordinates.
    x=0..15 left→right, y=0..15 top→bottom (screen-natural, y=0=top).

    The physical panel is column-serpentine:
      Even columns: bottom→top physically → y=0=top maps to (15-y)
      Odd  columns: top→bottom physically → y=0=top maps to y
    """
    if x % 2 == 0:
        return x * _PANEL16_COLS + (_PANEL16_COLS - 1 - y)
    else:
        return x * _PANEL16_COLS + y


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

# Physical panel dimensions (cols, rows) per wiring — used by effects
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

    Instantiated by wk.py using the internal wiring name derived from HARDWARE:
        wiring = Wiring("vertical" | "horizontal" | "matrix16")

    Methods:
        word_xy(x, y)   x=0..10, y=0..9 bottom→top  → physical index
        panel_xy(x, y)  x=0..W-1, y=0..H-1 top→bottom → physical index
        panel_dims       (cols, rows) of the full physical panel
    """

    def __init__(self, name: str):
        if name not in _WORD_BUILDERS:
            known = ", ".join(sorted(_WORD_BUILDERS))
            log.warning("Unknown wiring '%s', falling back to 'vertical'. Known: %s", name, known)
            name = "vertical"
        self.name       = name
        self._word_fn   = _WORD_BUILDERS[name]
        self._panel_fn  = _PANEL_BUILDERS[name]
        self.panel_dims = PANEL_DIMS[name]
        log.info("Wiring: %s  panel=%s", name, self.panel_dims)

    def word_xy(self, x: int, y: int) -> int:
        """Physical index for word grid position (x=col, y=row, y=0=bottom)."""
        return self._word_fn(x, y)

    def panel_xy(self, x: int, y: int) -> int:
        """Physical index for panel position (x=col, y=row, y=0=top)."""
        return self._panel_fn(x, y)
