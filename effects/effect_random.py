import random
import time
from effects.base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.02  # 50fps
    
    def draw(self):
        """Draw random LEDs with time overlay"""
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Draw random LEDs (background)
        num_leds = random.randint(20, 30)
        for _ in range(num_leds):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            color = self.word_clock.random_color(self.word_clock.rand_color)
            self.word_clock.setcolor_x_y(x, y, color)
        
        # Draw time on top (clears old words automatically)
        self.word_clock.update_clock()
