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
    
    def _generate_random_color(self):
        """Generate random color based on tint"""
        if self.tint == "blue":
            r = random.randint(29, 69)
            g = random.randint(31, 71)
            b = random.randint(105, 245)
        elif self.tint == "orange":
            r = random.randint(100, 155)
            g = random.randint(20, 40)
            b = random.randint(0, 2)
        elif self.tint == "red":
            r = random.randint(200, 255)
            g = random.randint(0, 50)
            b = random.randint(0, 50)
        elif self.tint == "green":
            r = random.randint(0, 50)
            g = random.randint(200, 255)
            b = random.randint(0, 50)
        elif self.tint == "purple":
            r = random.randint(150, 255)
            g = random.randint(0, 50)
            b = random.randint(150, 255)
        else:  # full random
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
        return (r, g, b)
    
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
        color = self._generate_random_color()

        # Apply current background brightness dynamically
        # This will use the latest slider value
        color = self.apply_background_brightness(color)
        
        self.word_clock.setcolor_x_y(x, y, color)
        
        # Overlay the time
        self.word_clock.update_clock()
