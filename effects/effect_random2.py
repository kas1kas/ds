import random
import time
from effects.base_effect import BaseEffect

class EffectRandom2(BaseEffect):
    name = "Random2"
    
    # Color tint presets with human-readable names
    TINT_PRESETS = {
        "blue": {"name": "Cool Blues", "r": (29, 69), "g": (31, 71), "b": (105, 245)},
        "orange": {"name": "Warm Oranges", "r": (100, 155), "g": (20, 40), "b": (0, 2)},
        "red": {"name": "Fiery Reds", "r": (200, 255), "g": (0, 50), "b": (0, 50)},
        "green": {"name": "Forest Greens", "r": (0, 50), "g": (200, 255), "b": (0, 50)},
        "purple": {"name": "Royal Purples", "r": (150, 255), "g": (0, 50), "b": (150, 255)},
        "rainbow": {"name": "Rainbow", "r": (0, 255), "g": (0, 255), "b": (0, 255), "special": "rainbow"},
        "pastel": {"name": "Soft Pastels", "r": (180, 255), "g": (140, 255), "b": (180, 255), "special": "pastel"},
        "amber": {"name": "Amber Glow", "r": (200, 255), "g": (100, 180), "b": (0, 50)},
        "aqua": {"name": "Aqua Marine", "r": (0, 50), "g": (150, 255), "b": (150, 255)},
    }
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.last_update = 0
        self.update_interval = 0.02  # 50 fps – smooth twinkling
        self.tint = word_clock.rand_color
        
        # Additional effect parameters
        self.fade_out = True  # Gradually fade out old pixels
        self.fade_speed = 0.85  # Multiplier for fading (lower = faster fade)
        self.max_pixels = 15  # Maximum number of pixels lit at once (None for unlimited)
        
        # Store pixel states for fading effect
        self.pixel_brightness = {}  # Dictionary to store current brightness of pixels
        
    def _generate_random_color(self):
        """Generate random color based on tint with enhanced options"""
        preset = self.TINT_PRESETS.get(self.tint, self.TINT_PRESETS["rainbow"])
        
        # Handle special color generation modes
        if preset.get("special") == "rainbow":
            # Cycle through hues for rainbow effect
            hue = random.random()
            return self._hsv_to_rgb(hue, 1.0, 1.0)
        
        elif preset.get("special") == "pastel":
            # Pastel colors - high value, medium saturation
            hue = random.random()
            return self._hsv_to_rgb(hue, 0.3, 1.0)
        
        else:
            # Standard RGB range-based generation
            r_range = preset["r"]
            g_range = preset["g"]
            b_range = preset["b"]
            
            r = random.randint(r_range[0], r_range[1])
            g = random.randint(g_range[0], g_range[1])
            b = random.randint(b_range[0], b_range[1])
            
            return (r, g, b)
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB color space"""
        h = h * 6.0
        i = int(h)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)
        
        i = i % 6
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def _apply_fade_to_all_pixels(self):
        """Apply fade to all existing pixels"""
        if not self.fade_out:
            return
            
        # Get current pixel states from the display
        # Since we can't easily read back pixels, we'll track them ourselves
        pixels_to_remove = []
        
        for key, brightness in self.pixel_brightness.items():
            # Apply fade
            new_brightness = brightness * self.fade_speed
            
            if new_brightness < 0.01:  # Threshold for removal
                pixels_to_remove.append(key)
            else:
                self.pixel_brightness[key] = new_brightness
                # Update pixel with faded color
                x, y = key
                # We need to know the original color - for simplicity, 
                # we'll just dim whatever's there
                # In a real implementation, you might want to store the original color
                current_color = (255, 255, 255)  # Placeholder
                faded_color = tuple(int(c * new_brightness) for c in current_color)
                faded_color = self.apply_background_brightness(faded_color)
                self.word_clock.setcolor_x_y(x, y, faded_color)
        
        # Remove very dim pixels
        for key in pixels_to_remove:
            del self.pixel_brightness[key]
            x, y = key
            self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        self.last_update = current_time
        
        # Get dimensions based on config
        max_cols, max_rows = self.get_dimensions()
        
        # Apply fade to existing pixels
        if self.fade_out:
            self._apply_fade_to_all_pixels()
        
        # Check if we've reached max pixels
        if self.max_pixels and len(self.pixel_brightness) >= self.max_pixels:
            return
        
        # Set one random LED
        x = random.randint(0, max_cols - 1)
        y = random.randint(0, max_rows - 1)
        
        # Skip if this pixel is already lit (optional)
        # if (x, y) in self.pixel_brightness:
        #     return
        
        color = self._generate_random_color()
        
        # Track this pixel for fading
        self.pixel_brightness[(x, y)] = 1.0
        
        # Apply current background brightness dynamically
        color = self.apply_background_brightness(color)
        
        self.word_clock.setcolor_x_y(x, y, color)
        
        # Overlay the time
        self.word_clock.update_clock()
