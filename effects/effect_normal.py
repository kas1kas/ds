import time
from effects.base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
    
    def draw(self):
        current_minute = time.localtime().tm_min
        if current_minute != self.last_minute:
            self.last_minute = current_minute
            self.word_clock.update_clock()
