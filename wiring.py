# -*- coding: utf-8 -*-
__version__ = "7.74"
# wiring.py — LED strip wiring layouts for the Woordklok
#
# Two coordinate spaces, two methods:
#
#   wiring.word_xy(x, y)
#     Word grid coordinates: x=0..10 left→right, y=0..9 bottom→top.
#     Used for rendering words and clearing the clock face.
#
#   wiring.panel_xy(x, y)
#     Panel coordinates: x=0..W-1 left→right, y=0..H-1 top→bottom.
#     Used by effects for full-panel rendering (screen-natural, y=0 is top).
#     For grid=11 variants, panel dimensions equal the word grid (11×10)
#     so this is rarely used, but is provided for consistency.
#
# Minute dot physical indices live in config_gen.json under MINUTE_DOTS,
# keyed by wiring name.  wiring.py does not store them.
#
# How to add a new wiring variant:
#   1. Define _word_xy_<name>(x, y) -> int
#   2. Define _panel_xy_<name>(x, y) -> int  (may reuse _word_xy if y-flip suffices)
#   3. Register both in _WORD_BUILDERS and _PANEL_BUILDERS.
#   4. Add its MINUTE_DOTS entry to config_gen.json.
#   5. Set  "WIRING": "<name>"  in config_loc.json.

import logging

log = logging.getLogger(__name__)

_WORD_ROWS = 10
_WORD_COLS = 11


# ---------------------------------------------------------------------------
# VERTICAL wiring — original column-strip serpentine
# ---------------------------------------------------------------------------

def _word_xy_vertical(x, y):
    """
    Column-strip serpentine. Strips run vertically, columns snake left→right.
    Even columns (x=0,2,...): bottom→top.  Odd columns (x=1,3,...): top→bottom.

    Physical indices:
      0, 1        = minute corners MLB / MLT
      2 .. 111    = word area (110 LEDs)
      112, 113    = minute corners MRB / MRT
    """
    if x % 2 == 0:
        return 2 + x * _WORD_ROWS + y
    else:
        return 2 + x * _WORD_ROWS + (_WORD_ROWS - 1 - y)


def _panel_xy_vertical(x, y):
    """
    Panel space for vertical grid=11: y=0 is the TOP row.
    Implemented as word_xy with y-axis flipped.
    """
    return _word_xy_vertical(x, _WORD_ROWS - 1 - y)

# ---------------------------------------------------------------------------
# HORIZONTAL wiring — horizontal-strip serpentine, top→bottom
#
# The LED strip starts at the TOP row and snakes downward.
#
# Physical layout:
#   0          = MLT  minute dot  (before top row, y=9)
#   1  ..  11  = row 9  top row    L→R
#   12         = MLB  minute dot  (after top row)
#   13 ..  23  = row 8             R→L
#   24 ..  34  = row 7             L→R
#   35 ..  45  = row 6             R→L
#   46 ..  56  = row 5             L→R
#   57 ..  67  = row 4             R→L
#   68 ..  78  = row 3             L→R
#   79 ..  89  = row 2             R→L
#   90 .. 100  = row 1             L→R
#   101        = MRB  minute dot  (after row 1, before bottom row)
#   102 .. 112 = row 0  bottom row R→L
#   113        = MRT  minute dot  (after bottom row)
# ---------------------------------------------------------------------------
 
def _word_xy_horizontal(x, y):
    """
    Word grid coords: y=0=bottom, y=9=top.
    Converts to strip_row (0=top strip, 9=bottom strip) then computes physical index.
    """
    strip_row = 9 - y   # y=9 → strip_row=0 (top), y=0 → strip_row=9 (bottom)
 
    if strip_row == 0:
        return 1 + x                                     # L→R
    elif 1 <= strip_row <= 7:
        base = 13 + (strip_row - 1) * _WORD_COLS
        if strip_row % 2 == 0:                           # even: L→R
            return base + x
        else:                                             # odd:  R→L
            return base + (_WORD_COLS - 1 - x)
    elif strip_row == 8:
        return 90 + x                                    # L→R
    elif strip_row == 9:
        return 102 + (_WORD_COLS - 1 - x)               # R→L
    else:
        raise ValueError(f"strip_row={strip_row} out of range")
 
def _panel_xy_horizontal(x, y):
    """
    Panel space for horizontal grid=11: y=0 is TOP.
    strip_row == y directly (both count from top).
    """
    strip_row = y
 
    if strip_row == 0:
        return 1 + x
    elif 1 <= strip_row <= 7:
        base = 13 + (strip_row - 1) * _WORD_COLS
        if strip_row % 2 == 0:
            return base + x
        else:
            return base + (_WORD_COLS - 1 - x)
    elif strip_row == 8:
        return 90 + x
    elif strip_row == 9:
        return 102 + (_WORD_COLS - 1 - x)
    else:
        raise ValueError(f"strip_row={strip_row} out of range")
 
# ---------------------------------------------------------------------------
# MATRIX16 wiring — 16×16 LED panel, column-serpentine
# ---------------------------------------------------------------------------

_PANEL16_COLS = 16
_PANEL16_ROWS = 16
_WORD_OFFSET_COL = 2   # word grid starts at panel column 2
_WORD_OFFSET_ROW = 3   # word grid starts at panel row 3 (y=0=bottom → panel_y=3+9=12)

def _word_xy_matrix16(x, y):
    """
    16x16 panel, word grid at offset (col+2, row+3).
    y=0 is the bottom clock row: panel_y = y + _WORD_OFFSET_ROW.
    y=0 → panel_y=3 (near bottom of column), y=9 → panel_y=12 (near top).

    Even panel columns: led = panel_x*16 + (15 - panel_y)
    Odd  panel columns: led = panel_x*16 + panel_y
    """
    panel_x = x + _WORD_OFFSET_COL
    panel_y = y + _WORD_OFFSET_ROW
    if panel_x % 2 == 0:
        return panel_x * _PANEL16_COLS + (_PANEL16_COLS - 1 - panel_y)
    else:
        return panel_x * _PANEL16_COLS + panel_y


def _panel_xy_matrix16(x, y):
    """
    16×16 panel, full-panel coordinates.
    x=0..15 left→right, y=0..15 top→bottom (screen-natural).
    Result: x*16 + y (uniform, column-major, y=0 at top).
    This matches what base_effect.map_coordinates + old setcolor produced.
    """
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

# Physical panel dimensions per wiring (used by effects via get_dimensions)
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
    Translates logical coordinates to physical LED strip indices.

    Two coordinate spaces:

      word_xy(x, y)   Word grid: x=0..10 L→R, y=0..9 bottom→top.
                      Used for rendering clock words and clearing the face.

      panel_xy(x, y)  Panel grid: x=0..W-1 L→R, y=0..H-1 top→bottom.
                      Used by effects for full-panel rendering.
                      For grid=11: W=11, H=10.  For grid=16: W=16, H=16.

    Minute dot physical indices are NOT stored here — read them from
    config_gen.json["MINUTE_DOTS"][wiring_name].

    Usage in wk.py:
        wiring_name      = config.get("WIRING", "vertical")
        self.wiring      = Wiring(wiring_name)
        self.minute_dots = config["MINUTE_DOTS"][wiring_name]

        # word LED:
        led = self.wiring.word_xy(x, y)

        # full-panel effect pixel:
        led = self.wiring.panel_xy(x, y)

        # panel dimensions for effect loops:
        cols, rows = self.wiring.panel_dims
    """

    def __init__(self, name: str):
        if name not in _WORD_BUILDERS:
            known = ", ".join(sorted(_WORD_BUILDERS))
            log.warning(
                "Unknown wiring '%s', falling back to 'vertical'. Known: %s",
                name, known
            )
            name = "vertical"

        self.name        = name
        self._word_fn    = _WORD_BUILDERS[name]
        self._panel_fn   = _PANEL_BUILDERS[name]
        self.panel_dims  = PANEL_DIMS[name]   # (cols, rows) for effect loops
        log.info("Wiring: %s  panel=%s", name, self.panel_dims)

    def word_xy(self, x: int, y: int) -> int:
        """Physical index for word grid position (x=col, y=row, y=0=bottom)."""
        return self._word_fn(x, y)

    def panel_xy(self, x: int, y: int) -> int:
        """Physical index for panel position (x=col, y=row, y=0=top)."""
        return self._panel_fn(x, y)
