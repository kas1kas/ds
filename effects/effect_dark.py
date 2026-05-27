import time
from effects.base_effect import BaseEffect


class EffectDark(BaseEffect):
    """
    Dark mode — screen off, one dim dot cycles slowly around the four
    minute-dot positions to show the clock is alive.

    Does not call update_clock() — no words, no time display, no dots
    from the minute system. Manages its own LEDs entirely.
    set_effect() already calls clear_all() before the first draw(),
    so no residual pixels from the previous effect will remain.
    """
    name = "Dark Mode"

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update     = 0
        self.update_interval = getattr(word_clock, 'light_interval', 1)
        self.dot_index       = 0   # which of the 4 dot positions is currently lit

    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        self.last_update = current_time

        dot_order   = self.word_clock.dot_order
        minute_dots = self.word_clock.minute_dots
        if not minute_dots:
            return

        # Blank every LED — no words, no background, nothing.
        for i in range(self.word_clock.led_count):
            self.word_clock.set_led_color(i, (0, 0, 0))

        # Light the current dot position in dot_dark_color.
        dot_key = dot_order[self.dot_index]
        led     = minute_dots.get(dot_key, -1) - 1   # 1-based → 0-based
        if led >= 0:
            self.word_clock.set_led_color(led, self.word_clock.dot_dark_color)

        self.dot_index = (self.dot_index + 1) % 4
        self.word_clock.strip.show()
