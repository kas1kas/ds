import time
import random
from .base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    description = "Random colors"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.1
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        x = random.randint(0, self.word_clock.columns - 1)
        y = random.randint(0, self.word_clock.rows - 1)
        
        # Generate random bright color
        color = (random.randint(100, 255), 
                random.randint(100, 255), 
                random.randint(100, 255))
        
        self.word_clock.setcolor_x_y(x, y, color)
        self.word_clock.update_clock()
