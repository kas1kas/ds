import random
import time
from effects.base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.02  # 20ms
        
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # DON'T clear here - let the main loop handle clearing
        # Just draw random LEDs ON TOP of whatever is there
        num_leds = random.randint(20, 30)
        for _ in range(num_leds):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            color = self.word_clock.random_color(self.word_clock.rand_color)
            self.word_clock.setcolor_x_y(x, y, color)
        
        # update_clock() will overlay the time WITHOUT clearing
        self.word_clock.update_clock()
