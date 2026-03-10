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
        self.update_interval = 0.1
        self.trail_length = 8
        
        # Create initial raindrops
        self._create_drops()
    
    def _create_drops(self):
        """Initialize raindrops"""
        self.drops = []
        max_cols, max_rows = self.get_dimensions()
        num_drops = max_cols
        for _ in range(num_drops):
            self._create_drop()
    
    def _create_drop(self):
        """Create a single raindrop using logical coordinates (0,0 at top-left)"""
        max_cols, max_rows = self.get_dimensions()
        col = random.randint(0, max_cols - 1)
        # Start above the grid (negative row means above the top)
        row = -random.randint(5, 15)
        speed = random.uniform(1.0, 3.0)
        drop = {
            'col': col,
            'row': row,  # Logical row: 0 = top, positive = down
            'speed': speed,
            'brightness': random.uniform(0.5, 1.0)
        }
        self.drops.append(drop)

    def draw(self):
        current_time = time.time()
        
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time

        # Get dimensions based on config - THIS WAS MISSING
        max_cols, max_rows = self.get_dimensions()

        # Clear screen based on config
        self.clear_screen()
        
        # Update and draw drops using logical coordinates
        for drop in self.drops:
            # Move drop DOWN (increase row to move down in logical coordinates)
            drop['row'] += drop['speed'] * 0.5
            
            # Draw trail
            for i in range(self.trail_length):
                # y_pos is logical coordinate: 0 = top, positive = down
                y_pos = int(drop['row'] - i)
                if 0 <= y_pos < max_rows:
                    brightness_factor = max(0, 1.0 - (i / self.trail_length))
                    brightness = int(255 * drop['brightness'] * brightness_factor)
                    
                    # Use logical coordinates - setcolor_x_y will handle physical mapping
                    self.word_clock.setcolor_x_y(drop['col'], y_pos, (0, brightness, 0))
            
            # Reset drop if it falls off screen (below bottom)
            if drop['row'] - self.trail_length > max_rows:
                drop['row'] = -random.randint(5, 15)  # Start above again
                drop['col'] = random.randint(0, max_cols - 1)
                drop['speed'] = random.uniform(1.0, 3.0)
                drop['brightness'] = random.uniform(0.5, 1.0)
        
        # Draw time
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot
