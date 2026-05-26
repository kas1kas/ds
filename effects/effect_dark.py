import time
from effects.base_effect import BaseEffect

class EffectDark(BaseEffect):
    name = "Dark Mode"
    manages_dots = True   # tells refresh_dots() to stay out of the way

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update     = 0
        self.update_interval = getattr(word_clock, 'light_interval', 1)
        self._initialised    = False

    def draw(self):
        """Only show moving minute dot."""
        # On the very first draw (e.g. dark mode is the startup default effect),
        # reset all dots to a clean state — set_effect() covers the switch case
        # but not the initial boot case.
        if not self._initialised:
            self.word_clock.reset_dots()
            self._initialised = True

        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        self.last_update = current_time
        self.clear_screen()
        self.word_clock.next_minuteled()
        self.word_clock.strip.show()
