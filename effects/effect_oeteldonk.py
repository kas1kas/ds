import random
import time
from effects.base_effect import BaseEffect

class EffectOeteldonk(BaseEffect):
    name = "Oeteldonk"
    description = "Oeteldonk vlag en carnaval"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.offset = 0
        self.last_update = 0
        self.update_interval = 0.05
        
    def draw(self):
        current_time = time.time()
        
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Get dimensions based on config
        max_cols, max_rows = self.get_dimensions()
        
        # Clear screen based on config
        self.clear_screen()
        
        # Update offset for moving bands (slow vertical scroll)
        self.offset = (self.offset + 1) % (max_rows * 2)
        
        # Draw the flag pattern
        for x in range(max_cols):
            for y in range(max_rows):
                # Calculate the band position with offset for animation
                band_y = (y + self.offset) % max_rows
                
                # Determine which third of the flag this pixel falls in
                if band_y < max_rows // 3:
                    # Top band - Red
                    color = (255, 0, 0)
                elif band_y < 2 * max_rows // 3:
                    # Middle band - White
                    color = (255, 255, 255)
                else:
                    # Bottom band - Yellow/Gold
                    color = (255, 215, 0)
                
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Draw time in white on top
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot
