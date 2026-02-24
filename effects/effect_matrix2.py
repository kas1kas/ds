import random
import time
from effects.base_effect import BaseEffect

class EffectMatrix2(BaseEffect):
    name = "Matrix 2"
    description = "you have to see it to believe it"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.drops = []
        self.last_update = 0
        self.update_interval = 0.1  # 100ms between updates
        self.trail_length = 8
        
        # Create initial raindrops
        num_drops = self.word_clock.columns
        for _ in range(num_drops):
            self._create_drop()
    
    def draw(self):
        current_time = time.time()
        
        # Control animation speed
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            # Move drops
            for drop in self.drops:
                drop['row'] += drop['speed']
                if drop['row'] - self.trail_length > self.word_clock.rows:
                    drop['row'] = -random.randint(1, self.trail_length)
                    drop['col'] = random.randint(0, self.word_clock.columns - 1)
                    drop['speed'] = random.uniform(0.5, 2.0)
                    drop['brightness'] = random.uniform(0.3, 1.0)
        
        # Clear grid
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        
        # Draw drops
        for drop in self.drops:
            for i in range(self.trail_length):
                y_pos = int(drop['row'] - i)
                if 0 <= y_pos < self.word_clock.rows:
                    brightness_factor = max(0, 1.0 - (i / self.trail_length))
                    brightness = int(255 * drop['brightness'] * brightness_factor)
                    self.word_clock.setcolor_x_y(drop['col'], y_pos, (0, brightness, 0))
        
        # Set time color to white and draw
        original_color = self.word_clock.letter_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_color
    
    def _create_drop(self):
        """Create a new raindrop"""
        col = random.randint(0, self.word_clock.columns - 1)
        row = -random.randint(1, self.trail_length)
        speed = random.uniform(0.5, 2.0)
        drop = {
            'col': col,
            'row': row,
            'speed': speed,
            'brightness': random.uniform(0.3, 1.0)
        }
        self.drops.append(drop)
