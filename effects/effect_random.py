import random
import time
from effects.base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update = 0
        self.update_interval = 0.02  # 50 fps – smooth twinkling
        
        # Store the tint for later use
        self.tint = word_clock.rand_color
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        self.last_update = current_time
                
        # Get dimensions based on config
        max_cols, max_rows = self.get_dimensions()
        
        # Set one random LED
        x = random.randint(0, max_cols - 1)
        y = random.randint(0, max_rows - 1)
        color = self.word_clock.random_color(self.tint)
        self.word_clock.setcolor_x_y(x, y, color)
        
        # Overlay the time
        self.word_clock.update_clock()
