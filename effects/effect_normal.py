import time
from effects.base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def draw(self):
        """Draw the clock every frame"""
        self.word_clock.update_clock()
