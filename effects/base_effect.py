# -*- coding: utf-8 -*-
__version__ = "7.80"
import logging

class BaseEffect:
    """Base class for all effects."""

    name        = "Base Effect"
    description = ""

    @classmethod
    def get_variants(cls):
        default_id = cls.__name__.lower().replace('effect', '')
        return [(default_id, cls.name)]

    def __init__(self, word_clock, variant_id=None):
        self.word_clock = word_clock
        self.logger     = logging.getLogger(f"effect.{self.__class__.__name__}")
        self.variant_id = variant_id

    def get_dimensions(self):
        """
        Return the (cols, rows) to iterate over for this effect.

        effect_full_panel=True  → full physical panel (16×16 for matrix16, 11×10 for grid=11).
        effect_full_panel=False → word grid area only (11×10).

        Coordinates match setcolor_x_y convention: y=0 is always TOP for all hardware.
        """
        if self.word_clock.effect_full_panel:
            return self.word_clock.wiring.panel_dims   # (cols, rows) from wiring
        else:
            return self.word_clock.clock_columns, self.word_clock.clock_rows

    def map_coordinates(self, x, y):
        """
        Previously applied a y-inversion workaround for the 16×16 panel.
        No longer needed — wiring.panel_xy handles all panel geometry correctly.
        Returns (x, y) unchanged; kept for backward compatibility with existing effects.
        """
        return x, y

    def clear_screen(self):
        """
        Clear the effect area to black using setcolor_x_y().

        effect_full_panel=True:  clears the full panel (e.g. 16x16)
        effect_full_panel=False: clears the word grid area (11x10)

        Uses setcolor_x_y() in both cases — y=0=top for all hardware.
        Does NOT call cls() or clear_all() — internal wk.py concerns.
        """
        cols, rows = self.get_dimensions()
        for x in range(cols):
            for y in range(rows):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))

    def apply_background_brightness(self, color):
        factor = self.word_clock.background_brightness_factor
        if factor >= 1.0:
            return color
        return (int(color[0]*factor), int(color[1]*factor), int(color[2]*factor))

    def get_background_brightness(self):
        return self.word_clock.background_brightness_factor

    def draw(self):
        """Draw one frame. Called every loop iteration."""
        pass
