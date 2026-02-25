import time
import math
import random
from effects.base_effect import BaseEffect

class EffectRainbow(BaseEffect):
    name = "Rainbow"
    description = "Animated rainbow patterns"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.j = 0
        self.last_frame_time = 0
        self.frame_delay = 0.01  # 10ms for smooth 100fps animation
        self.effect = 0  # Default to first effect
        self.effect_names = [
            "Diagonal",
            "Horizontal",
            "Vertical",
            "Circular",
            "Spiral",
            "Wave",
            "Twinkle"
        ]
        self.center_x = (word_clock.columns - 1) / 2
        self.center_y = (word_clock.rows - 1) / 2
    
    def kwheel(self, pos):
        """Color wheel - returns (r,g,b) tuple"""
        pos = pos & 255
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)
    
    def set_sub_effect(self, effect_num):
        """Change the rainbow pattern"""
        try:
            effect_num = int(effect_num)
            if 0 <= effect_num < len(self.effect_names):
                self.effect = effect_num
                self.j = 0  # Reset animation
                return True
        except ValueError:
            pass
        return False
    
    def draw(self):
        """Draw one frame of the rainbow animation"""
        current_time = time.time()
        
        # Control frame rate for smooth animation
        if current_time - self.last_frame_time < self.frame_delay:
            return
        
        self.last_frame_time = current_time
        
        # Clear the display for the new frame
        self.word_clock.cls()
        
        # Draw the rainbow pattern
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                if self.effect == 0:  # Diagonal
                    k = (x * y + self.j) & 255
                    
                elif self.effect == 1:  # Horizontal
                    k = (x + self.j) & 255
                    
                elif self.effect == 2:  # Vertical
                    k = (y + self.j) & 255
                    
                elif self.effect == 3:  # Circular ripple
                    dx = x - self.center_x
                    dy = y - self.center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(distance * 10 + self.j) & 255
                    
                elif self.effect == 4:  # Spiral
                    dx = x - self.center_x
                    dy = y - self.center_y
                    angle = math.atan2(dy, dx)
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(angle/math.pi * 128 + distance * 5 + self.j) & 255
                    
                elif self.effect == 5:  # Wave
                    wave = math.sin(x/2.0 + self.j/20.0) * 5
                    k = int(y + wave + self.j) & 255
                    
                elif self.effect == 6:  # Twinkle
                    # For twinkle, we use a special approach
                    if x == 0 and y == 0:
                        self._update_twinkle()
                    # Skip regular pixel drawing for twinkle
                    continue
                
                # Set the color for this pixel
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # For twinkle effect, we've already set pixels in _update_twinkle
        if self.effect == 6:
            # Additional random twinkles
            for _ in range(5):
                x = random.randint(0, self.word_clock.columns - 1)
                y = random.randint(0, self.word_clock.rows - 1)
                k = (x + y + self.j) & 255
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Draw the time on top
        self.word_clock.update_clock()
        
        # Advance animation
        self.j = (self.j + 1) % (256 * 5)
    
    def _update_twinkle(self):
        """Helper for twinkle effect - update random pixels"""
        for _ in range(15):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            k = (x + y + self.j) & 255
            color = self.kwheel(k)
            self.word_clock.setcolor_x_y(x, y, color)
    
    def get_settings_template(self):
        """Return HTML for rainbow effect settings"""
        # Create options with current effect selected
        options = []
        for i, name in enumerate(self.effect_names):
            selected = "selected" if i == self.effect else ""
            options.append(f'<option value="{i}" {selected}>{name}</option>')
        
        options_html = ''.join(options)
        
        return f'''
        <div class="rainbow-settings">
            <label for="rainbow_pattern"><b>Rainbow Pattern:</b></label>
            <select id="rainbow_pattern" onchange="setRainbowPattern(this.value)">
                {options_html}
            </select>
        </div>
        <script>
        function setRainbowPattern(value) {{
            fetch('/rainbow/set_effect', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{sub_effect: parseInt(value)}})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'success') {{
                    console.log('Rainbow pattern changed to ' + value);
                }}
            }})
            .catch(error => console.error('Error:', error));
        }}
        </script>
        '''
