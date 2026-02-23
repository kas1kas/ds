import time
import random
from .base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Rand2"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.001
        self.tint = word_clock.rand_color
    
    def random_color(self):
        if self.tint == "blue":
            return (random.randint(29, 69), random.randint(31, 71), random.randint(105, 245))
        else:  # orange
            return (random.randint(100, 155), random.randint(20, 40), random.randint(0, 2))
    
    def update(self):
        if time.time() - self.last_update < self.update_interval:
            return
        self.last_update = time.time()
        
        x = random.randint(0, self.word_clock.columns - 1)
        y = random.randint(0, self.word_clock.rows - 1)
        self.word_clock.setcolor_x_y(x, y, self.random_color())
        self.word_clock.update_clock()
