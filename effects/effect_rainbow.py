import time
import math
import random
from .base_effect import BaseEffect

class EffectRainbow(BaseEffect):
    name = "Rainbow"
    description = "Animated rainbow patterns"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.j = 0
        self.last_frame_time = 0
        self.frame_delay = 0.05  # 50ms between frames
        self.effect = 0  # Sub-effect for rainbow variations
        self.effect_names = ["Diagonal", "Horizontal", "Vertical", "Circular", 
                            "Spiral", "Wave", "Twinkle"]
        self.center_x = (word_clock.columns - 1) / 2
        self.center_y = (word_clock.rows - 1) / 2
        
    def kwheel(self, pos):
        """Color wheel - input 0-255, returns RGB tuple"""
        pos = pos % 256
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)
    
    def start(self):
        self.logger.info(f"Starting rainbow effect")
        self.j = 0
        self.last_frame_time = 0
        
    def stop(self):
        self.logger.info(f"Stopping rainbow effect")
    
    def set_sub_effect(self, effect_num):
        """Change the rainbow pattern"""
        if 0 <= effect_num < len(self.effect_names):
            self.effect = effect_num
            self.j = 0  # Reset animation
            self.logger.info(f"Rainbow pattern set to: {self.effect_names[effect_num]}")
            return True
        return False
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_delay:
            return
        
        self.last_frame_time = current_time
        
        # Clear the display first
        self.word_clock.cls()
        
        # Draw rainbow pattern
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
                    k = int(angle * 50 + distance * 10 + self.j) & 255
                    
                elif self.effect == 5:  # Wave
                    wave = math.sin(x * 0.8 + self.j * 0.1) * 3
                    k = int(y * 20 + wave * 10 + self.j) & 255
                    
                elif self.effect == 6:  # Twinkle - random pixels
                    # Use a different calculation for twinkle
                    random.seed(x * 100 + y + self.j)
                    k = random.randint(0, 255)
                
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Overlay the time (this will also call strip.show())
        self.word_clock.update_clock()
        
        # Advance animation
        self.j = (self.j + 1) % (256 * 5)
    
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
                    console.log('Rainbow pattern changed');
                }}
            }});
        }}
        </script>
        '''
