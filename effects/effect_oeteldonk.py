import random
import time
from effects.base_effect import BaseEffect

class EffectOeteldonk(BaseEffect):
    name = "Oeteldonk"
    description = "Oeteldonk vlag en carnaval"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
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
        
        # Calculate band heights with middle band taking any remainder
        band_height = max_rows // 3
        remainder = max_rows % 3
        
        # Top band height
        top_height = band_height
        # Middle band gets the remainder
        middle_height = band_height + remainder
        # Bottom band height
        bottom_height = band_height
        
        # Draw the static flag pattern
        for x in range(max_cols):
            for y in range(max_rows):
                # Determine which third of the flag this pixel falls in
                if y < top_height:
                    # Top band - Red
                    color = (255, 0, 0)
                elif y < top_height + middle_height:
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
