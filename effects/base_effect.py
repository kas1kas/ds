# -*- coding: utf-8 -*-
__version__ = "7.74"

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

        Coordinates returned here match what setcolor_x_y expects:
          full panel: y=0 is TOP  (panel space, wiring.panel_xy)
          word grid:  y=0 is BOTTOM (word space, wiring.word_xy)
        """
        if self.word_clock.effect_full_panel:
            return self.word_clock.wiring.panel_dims   # (cols, rows) from wiring
        else:
            return self.word_clock.clock_columns, self.word_clock.clock_rows

    def clear_screen(self):
        """
        Clear LEDs for the current effect area.

        Full panel: iterates panel dimensions via setcolor_x_y (panel coords, y=0=top).
        Word area:  calls cls() which uses word coords (y=0=bottom).
        """
        if self.word_clock.effect_full_panel:
            cols, rows = self.word_clock.wiring.panel_dims
            for x in range(cols):
                for y in range(rows):
                    self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        else:
            self.word_clock.cls()

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
