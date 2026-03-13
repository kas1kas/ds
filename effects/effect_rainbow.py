import time
import math
import random
from effects.base_effect import BaseEffect

class EffectRainbow(BaseEffect):
    name = "Rainbow"  # Base name, will be overridden by variants
    description = "Animated rainbow patterns"
    
    @classmethod
    def get_variants(cls):
        """Return seven variants of rainbow effect"""
        patterns = [
            ("rainbow_diagonal", "Rainbow Diagonal"),
            ("rainbow_horizontal", "Rainbow Horizontal"),
            ("rainbow_vertical", "Rainbow Vertical"),
            ("rainbow_circular", "Rainbow Circular"),
            ("rainbow_spiral", "Rainbow Spiral"),
            ("rainbow_wave", "Rainbow Wave"),
            ("rainbow_twinkle", "Rainbow Twinkle")
        ]
        return patterns
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        # Map variant_id to pattern index
        pattern_map = {
            "rainbow_diagonal": 0,
            "rainbow_horizontal": 1,
            "rainbow_vertical": 2,
            "rainbow_circular": 3,
            "rainbow_spiral": 4,
            "rainbow_wave": 5,
            "rainbow_twinkle": 6
        }
        self.pattern = pattern_map.get(variant_id, 0)
        
        # Set display name based on pattern
        pattern_names = [
            "Rainbow Diagonal",
            "Rainbow Horizontal",
            "Rainbow Vertical",
            "Rainbow Circular",
            "Rainbow Spiral",
            "Rainbow Wave",
            "Rainbow Twinkle"
        ]
        self.name = pattern_names[self.pattern]
        
        self.j = 0
        self.last_frame_time = 0
        self.frame_delay = 0.01
    
    def kwheel(self, pos):
        pos = pos & 255
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_delay:
            return
        
        self.last_frame_time = current_time
        
        # Use clear_screen() instead of cls() to respect effect_full_panel setting
        self.clear_screen()

        # Get background brightness factor
        bg_factor = self.word_clock.background_brightness_factor
        
        # Get dimensions based on config
        max_cols, max_rows = self.get_dimensions()
        
        # Calculate centers based on current dimensions
        center_x = (max_cols - 1) / 2
        center_y = (max_rows - 1) / 2
        
        for x in range(max_cols):
            for y in range(max_rows):
                if self.pattern == 0:  # Diagonal
                    k = (x * y + self.j) & 255
                elif self.pattern == 1:  # Horizontal
                    k = (x + self.j) & 255
                elif self.pattern == 2:  # Vertical
                    k = (y + self.j) & 255
                elif self.pattern == 3:  # Circular
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(distance * 10 + self.j) & 255
                elif self.pattern == 4:  # Spiral
                    dx = x - center_x
                    dy = y - center_y
                    angle = math.atan2(dy, dx)
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(angle/math.pi * 128 + distance * 5 + self.j) & 255
                elif self.pattern == 5:  # Wave
                    wave = math.sin(x/2.0 + self.j/20.0) * 5
                    k = int(y + wave + self.j) & 255
                elif self.pattern == 6:  # Twinkle
                    # Simple hash for twinkling
                    k = (x * 37 + y * 53 + self.j) & 255
                
                color = self.kwheel(k)

                # Apply background dimming to all pixels
                # The time overlay will be drawn bright on top
                if bg_factor < 1.0:
                    color = (
                        int(color[0] * bg_factor),
                        int(color[1] * bg_factor),
                        int(color[2] * bg_factor)
                    )
                
                self.word_clock.setcolor_x_y(x, y, color)
        
        self.word_clock.update_clock()
        self.j = (self.j + 1) % (256 * 5)
