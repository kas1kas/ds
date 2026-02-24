import random
import time
from effects.base_effect import BaseEffect  # Absolute import

class EffectRandom(BaseEffect):
    name = "Random"
    description = "Randomly colored LEDs"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.05  # 50ms for smooth animation
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear and set random LEDs
        self.word_clock.cls()
        
        # Set 10-20 random LEDs per frame
        num_leds = random.randint(10, 20)
        for _ in range(num_leds):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            self.word_clock.setcolor_x_y(x, y, (r, g, b))
        
        # Show time overlay
        self.word_clock.update_clock()
    
    def get_settings_template(self):
        return "<div>Random mode - no additional settings</div>"
