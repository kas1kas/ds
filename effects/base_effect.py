# -*- coding: utf-8 -*-
__version__ = "8.00"
import logging


class BaseEffect:
    """Base class for all Woordklok effects."""

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
        Return (cols, rows) for this effect's coordinate space.

        effect_full_panel=True  → full physical panel (16×16 or 11×10).
        effect_full_panel=False → word grid area only (11×10).

        All coordinates are y=0=top for all hardware.
        """
        if self.word_clock.effect_full_panel:
            return self.word_clock.wiring.panel_dims
        else:
            return self.word_clock.clock_columns, self.word_clock.clock_rows

    def clear_screen(self):
        """
        Clear the effect area to black using setcolor_x_y().

        Covers the full panel when effect_full_panel=True,
        or the word grid only when effect_full_panel=False.
        Does NOT call clear_all() — that is wk.py's concern for effect switches.
        """
        cols, rows = self.get_dimensions()
        for x in range(cols):
            for y in range(rows):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))

    def apply_background_brightness(self, color):
        factor = self.word_clock.background_brightness_factor
        if factor >= 1.0:
            return color
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor),
        )

    def get_background_brightness(self):
        return self.word_clock.background_brightness_factor

    def draw(self):
        """
        Draw one frame. Called every loop iteration by run_clock().

        strip.show() contract:
          Effects that overlay clock words must call
          self.word_clock.update_clock() as the LAST step — it is the
          only place that calls strip.show(), so all pixel writes are
          buffered and flushed together.

          Effects that do NOT overlay the clock (e.g. EffectDark) must
          call self.word_clock.strip.show() themselves at the end.
        """
        pass
