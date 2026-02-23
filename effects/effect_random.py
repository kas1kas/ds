import time
import random
from .base_effect import BaseEffect

class EffectRandom(BaseEffect):
    name = "Random"
    description = "Fast random colors with tint"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.01  # Much faster - 10ms (original was very fast)
        self.tint = word_clock.rand_color  # Get tint from config (blue or orange)
    
    def random_color(self):
        """Use the word_clock's random_color method"""
        return self.word_clock.random_color(self.tint)
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Get random position
        x = random.randint(0, self.word_clock.columns - 1)
        y = random.randint(0, self.word_clock.rows - 1)
        
        # Get random color using the original method with tint
        color = self.random_color()
        
        # Set the LED
        self.word_clock.setcolor_x_y(x, y, color)
        
        # Update clock display (shows time with random colors behind it)
        self.word_clock.update_clock()
    
    def get_settings_template(self):
        """Show current tint setting"""
        return f"""
        <div class="random-settings">
            <p>Random effect with <b>{self.tint}</b> tint</p>
            <p><small>To change tint, edit RAND_COLOR in config</small></p>
        </div>
        """
