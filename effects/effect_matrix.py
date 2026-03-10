import random
import time
from effects.base_effect import BaseEffect

class EffectMatrix(BaseEffect):
    name = "the Matrix"
    description = "You have to see it to believe it"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.drops = []
        self.last_update = 0
        self.update_interval = 0.1  # 100ms between updates (fixed)
        self.trail_length = 8        # fixed trail length
        
        # Create initial raindrops
        self._create_drops()
    
    def _create_drops(self):
        """Initialize raindrops"""
        self.drops = []
        num_drops = self.word_clock.columns  # one per column
        for _ in range(num_drops):
            self._create_drop()
    
    def _create_drop(self):
        """Create a single raindrop"""
        col = random.randint(0, self.word_clock.columns - 1)
        row = -random.randint(5, 15)  # start above grid
        speed = random.uniform(1.0, 3.0)  # fixed speed range
        drop = {
            'col': col,
            'row': row,
            'speed': speed,
            'brightness': random.uniform(0.5, 1.0)
        }
        self.drops.append(drop)
    
    def draw(self):
        current_time = time.time()
        
        # Control animation speed
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear the grid (word area)
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        
        # Update and draw drops
        for drop in self.drops:
            # Move drop down
            drop['row'] += drop['speed'] * 0.5  # smooth movement
            
            # Draw trail
            for i in range(self.trail_length):
                y_pos = int(drop['row'] - i)
                if 0 <= y_pos < self.word_clock.rows:
                    # Fade out with distance from head
                    brightness_factor = max(0, 1.0 - (i / self.trail_length))
                    brightness = int(255 * drop['brightness'] * brightness_factor)
                    self.word_clock.setcolor_x_y(drop['col'], y_pos, (0, brightness, 0))
            
            # Reset drop if it falls off screen
            if drop['row'] - self.trail_length > self.word_clock.rows:
                drop['row'] = -random.randint(5, 15)
                drop['col'] = random.randint(0, self.word_clock.columns - 1)
                drop['speed'] = random.uniform(1.0, 3.0)
                drop['brightness'] = random.uniform(0.5, 1.0)
        
        # Draw time in white (save and restore original color)
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot
