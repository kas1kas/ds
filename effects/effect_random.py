import random
import time
from effects.base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.02  # 20ms for super smooth 50fps animation
        
    def draw(self):
        """Draw one frame - sets random LEDs with colors from config"""
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear the display
        self.word_clock.cls()
        
        # Set 20-30 random LEDs per frame (tunable for visual density)
        num_leds = random.randint(20, 30)
        for _ in range(num_leds):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            
            # Use the random_color method from word_clock with configured tint
            color = self.word_clock.random_color(self.word_clock.rand_color)
            self.word_clock.setcolor_x_y(x, y, color)
        
        # Show the time overlay
        self.word_clock.update_clock()
