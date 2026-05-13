# wiring.py — LED strip wiring layouts for the Woordklok
#
# Owns all geometry: translates logical clock position (x, y) directly to
# the physical LED strip index for a given hardware build.
#
#   x = column, 0 = leftmost,  10 = rightmost
#   y = row,    0 = bottom,     9 = top
#
# config_gen.json word coordinates are stored as a flat index
# (grid_index = y * 11 + x) and stay unchanged forever.
#
# How to add a new wiring variant:
#   1. Define _xy_to_<name>(x, y) -> int
#   2. Define its minute-dot dict (MLT/MLB/MRB/MRT -> physical index)
#   3. Register both in _BUILDERS and _MINUTE_DOTS.
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
    Physical 0,1 = minute corners MLB/MLT.
    Physical 2..111 = word area.
    Physical 112,113 = minute corners MRB/MRT.
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
        return 1 + x                            # L→R
    elif 1 <= y <= 7:
        base = 13 + (y - 1) * _COLS
        if y % 2 == 0:                          # even rows: L→R
            return base + x
        else:                                   # odd rows:  R→L
            return base + (_COLS - 1 - x)
    elif y == 8:
        return 90 + x                           # even: L→R
    elif y == 9:
        return 102 + (_COLS - 1 - x)           # odd:  R→L
    else:
        raise ValueError(f"y={y} out of range 0..9")


# ---------------------------------------------------------------------------
# Minute-dot physical indices per wiring variant
# ---------------------------------------------------------------------------

_MINUTE_DOTS = {
    "vertical": {
        "MLT": 1,
        "MLB": 0,
        "MRB": 112,
        "MRT": 113,
    },
    "horizontal": {
        "MLT": 0,
        "MLB": 12,
        "MRB": 101,
        "MRT": 113,
    },
    "matrix16": {
        "MLT": 14,
        "MLB": 1,
        "MRB": 225,
        "MRT": 238,
    },
}

_BUILDERS = {
    "vertical":   _xy_to_vertical,
    "horizontal": _xy_to_horizontal,
    "matrix16":   None,   # panel geometry handled separately in wk.py
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Wiring:
    """
    Translates logical clock position (x, y) to physical strip index.

    Usage in wk.py:
        self.wiring = Wiring(config.get("WIRING", "vertical"))

        # word LED at column x, row y:
        led_index = self.wiring.xy(x, y)

        # minute dot:
        led_index = self.wiring.minute_dot("MLT")
    """

    def __init__(self, name: str):
        if name not in _BUILDERS:
            known = ", ".join(sorted(_BUILDERS))
            log.warning(
                "Unknown wiring '%s', falling back to 'vertical'. Known: %s",
                name, known
            )
            name = "vertical"

        self.name         = name
        self._xy_fn       = _BUILDERS[name]
        self._minute_dots = _MINUTE_DOTS[name]
        log.info("Wiring: %s", name)

    def xy(self, x: int, y: int) -> int:
        """Return physical strip index for logical clock position (x, y)."""
        return self._xy_fn(x, y)

    def minute_dot(self, name: str) -> int:
        """Return physical strip index for a named minute dot (MLT/MLB/MRB/MRT)."""
        return self._minute_dots[name]
