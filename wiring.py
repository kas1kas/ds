# -*- coding: utf-8 -*-
__version__ = "7.72"
# wiring.py — LED strip wiring layouts for the Woordklok
#
# Translates logical clock position (x, y) to physical LED strip index.
#
#   x = column, 0 = leftmost,  10 = rightmost
#   y = row,    0 = bottom,     9 = top
#
# Minute dot physical indices are NOT stored here — they live in
# config_gen.json under MINUTE_DOTS, keyed by wiring name.
# wk.py reads them directly from config and uses set_led_color() with
# those indices — no translation needed because the config values are
# already the correct physical indices for each wiring variant.
#
# How to add a new wiring variant:
#   1. Define _xy_to_<name>(x, y) -> int
#   2. Register it in _BUILDERS.
#   3. Add its MINUTE_DOTS entry to config_gen.json.
#   4. Set  "WIRING": "<name>"  in config_loc.json.

import logging

log = logging.getLogger(__name__)

_ROWS = 10
_COLS = 11


# ---------------------------------------------------------------------------
# Wiring geometry functions — one per hardware variant
# ---------------------------------------------------------------------------

def _xy_to_vertical(x, y):
    """
    Original column-strip serpentine.
    Strips run vertically; columns snake left→right.
    Even columns (x=0,2,4,...) run bottom→top.
    Odd  columns (x=1,3,5,...) run top→bottom.

    Physical layout:
      0, 1       = minute corners MLB / MLT
      2 .. 111   = word area (110 LEDs)
      112, 113   = minute corners MRB / MRT
    """
    if x % 2 == 0:
        return 2 + (x * _ROWS) + y
    else:
        return 2 + (x * _ROWS) + (_ROWS - 1 - y)


def _xy_to_horizontal(x, y):
    """
    New horizontal-strip serpentine.
    Strips run horizontally; rows snake bottom→top.
    Even rows (y=0,2,4,...) run left→right.
    Odd  rows (y=1,3,5,...) run right→left.

    Physical layout:
      0          = MLT  minute dot  (before row 0)
      1  ..  11  = row 0  L→R
      12         = MLB  minute dot  (after row 0)
      13 ..  23  = row 1  R→L
      24 ..  34  = row 2  L→R
      35 ..  45  = row 3  R→L
      46 ..  56  = row 4  L→R
      57 ..  67  = row 5  R→L
      68 ..  78  = row 6  L→R
      79 ..  89  = row 7  R→L
      90 .. 100  = row 8  L→R
      101        = MRB  minute dot  (after row 8, before row 9)
      102 .. 112 = row 9  R→L
      113        = MRT  minute dot  (after row 9)
    """
    if y == 0:
        return 1 + x
    elif 1 <= y <= 7:
        base = 13 + (y - 1) * _COLS
        if y % 2 == 0:          # even rows: L→R
            return base + x
        else:                    # odd rows:  R→L
            return base + (_COLS - 1 - x)
    elif y == 8:
        return 90 + x
    elif y == 9:
        return 102 + (_COLS - 1 - x)
    else:
        raise ValueError(f"y={y} out of range 0..9")


def _xy_to_matrix16(x, y):
    """
    16×16 LED panel, column-serpentine wiring.
    The 11×10 word grid is positioned at panel offset (col+2, row+3).

    Panel column direction:
      Even panel columns (panel_x=2,4,6,...): panel_y=0 is BOTTOM, increases upward
        → formula: panel_x*16 + (15 - panel_y)
      Odd  panel columns (panel_x=3,5,7,...): panel_y=0 is TOP, increases downward
        → formula: panel_x*16 + panel_y

    y=0 is the bottom clock row, y=9 is the top clock row.
    """
    panel_x = x + 2
    panel_y = y + 3
    if panel_x % 2 == 0:
        return panel_x * 16 + (15 - panel_y)
    else:
        return panel_x * 16 + panel_y


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_BUILDERS = {
    "vertical":   _xy_to_vertical,
    "horizontal": _xy_to_horizontal,
    "matrix16":   _xy_to_matrix16,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Wiring:
    """
    Translates logical clock position (x, y) to a physical LED strip index.

    Minute dot indices are NOT the responsibility of this class.
    They are read from config_gen.json["MINUTE_DOTS"][wiring_name] by wk.py.

    Usage in wk.py:
        wiring_name    = config.get("WIRING", "vertical")
        self.wiring    = Wiring(wiring_name)
        self.minute_dots = config["MINUTE_DOTS"][wiring_name]

        # word LED:
        led_index = self.wiring.xy(x, y)

        # minute dot (raw config value, no translation needed):
        led_index = self.minute_dots["MLT"]
    """

    def __init__(self, name: str):
        if name not in _BUILDERS:
            known = ", ".join(sorted(_BUILDERS))
            log.warning(
                "Unknown wiring '%s', falling back to 'vertical'. Known: %s",
                name, known
            )
            name = "vertical"

        self.name   = name
        self._xy_fn = _BUILDERS[name]
        log.info("Wiring: %s", name)

    def xy(self, x: int, y: int) -> int:
        """Return physical strip index for logical clock position (x, y)."""
        return self._xy_fn(x, y)
