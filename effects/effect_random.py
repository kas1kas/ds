import time
import random
from .base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    description = "Fast random colors with tint"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.001  # Fast - 1ms
        self.tint = word_clock.rand_color  # Get tint from config
    
    def random_color(self):
        """Random color based on tint - moved from WordClock class"""
        if self.tint == "blue":
            r = random.randint(29, 69)    # shades of blue 
            g = random.randint(31, 71)
            b = random.randint(105, 245)
        elif self.tint == "orange":
            r = random.randint(100, 155)  # shades of orange 
            g = random.randint(20, 40)
            b = random.randint(0, 2)
        else:
            # Default to blue if tint is invalid
            r = random.randint(29, 69)
            g = random.randint(31, 71)
            b = random.randint(105, 245)
        return (r, g, b)
    
    def start(self):
        """Called when effect starts"""
        self.logger.info(f"Starting random effect with {self.tint} tint")
        # Clear screen first
        self.word_clock.cls()
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Get random position
        x = random.randint(0, self.word_clock.columns - 1)
        y = random.randint(0, self.word_clock.rows - 1)
        
        # Get random color using local method
        color = self.random_color()
        
        # Set the LED
        self.word_clock.setcolor_x_y(x, y, color)
        
        # Update clock display
        self.word_clock.update_clock()
    
    def get_settings_template(self):
        """Show current tint setting"""
        return f"""
        <div class="random-settings">
            <p>Random effect - <b>{self.tint}</b> tint</p>
            <p>Speed: Fast (original)</p>
        </div>
        """
