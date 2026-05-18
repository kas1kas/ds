import time
from effects.base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal"

    def draw(self):
        self.clear_screen()
        self.word_clock.update_clock()
