import random
import time
import math
from effects.base_effect import BaseEffect

class EffectOeteldonk2(BaseEffect):
    name = "Oeteldonk2"
    description = "Oeteldonk vlag en carnaval"

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update = 0
        self.update_interval = 0.1  # 100ms between updates
        self.phase = 0
        self.band_position = 0
        self.band_direction = 1

    def _get_oeteldonk_color(self, x, y, max_cols, max_rows):
        """Return Oeteldonk theme colors based on position and time"""
        
        # Calculate normalized position (0-1 range)
        nx = x / max_cols
        ny = y / max_rows
        
        # Add moving wave effect
        wave = math.sin(self.phase + x * 0.5) * 0.3
        
        # Oeteldonk flag colors: red, white, yellow (gold)
        # Create a striped pattern that moves
        
        # Determine which stripe this pixel belongs to
        stripe = int((ny + wave) * 6) % 6
        
        if stripe == 0 or stripe == 1:
            # Red stripe
            r = 255
            g = int(50 + math.sin(self.phase + x) * 30)
            b = int(50 + math.cos(self.phase + y) * 30)
        elif stripe == 2 or stripe == 3:
            # White stripe
            r = 255
            g = 255
            b = 200
        else:
            # Yellow/Gold stripe
            r = 255
            g = 215
            b = 0
        
        # Add some sparkle (carnaval confetti effect)
        if random.random() < 0.02:
            # Random bright color for confetti
            r = random.randint(200, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
        
        # Moving band effect (like a waving flag)
        band = math.sin(self.band_position + y * 0.3) * 0.5 + 0.5
        r = int(r * (0.7 + band * 0.3))
        g = int(g * (0.7 + band * 0.3))
        b = int(b * (0.7 + band * 0.3))
        
        return (r, g, b)

    def draw(self):
        current_time = time.time()
        
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Update animation parameters
        self.phase += 0.1
        self.band_position += 0.05 * self.band_direction
        
        # Reverse band direction at boundaries
        if self.band_position > math.pi * 2 or self.band_position < 0:
            self.band_direction *= -1
            self.band_position = max(0, min(self.band_position, math.pi * 2))
        
        # Get dimensions based on config (full panel or clock area)
        max_cols, max_rows = self.get_dimensions()
        
        # Clear screen based on config
        self.clear_screen()
        
        # Draw Oeteldonk pattern
        for x in range(max_cols):
            for y in range(max_rows):
                color = self._get_oeteldonk_color(x, y, max_cols, max_rows)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Draw time in white on top
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot
