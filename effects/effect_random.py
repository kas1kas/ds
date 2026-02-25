import random
import time
from effects.base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update = 0
        self.update_interval = 0.02  # 50 fps – smooth twinkling
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        self.last_update = current_time
        
        # Set one random LED with the configured color tint
        self.word_clock.set_random_led(self.word_clock.rand_color)
        
        # Overlay the time (this also calls strip.show())
        self.word_clock.update_clock()
