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
        self.last_update = 0
        self.update_interval = 0.02  # 20ms for smooth 50fps animation
        self.effect = 0  # Sub-effect
        self.effect_names = ["Diagonal", "Horizontal", "Vertical", "Circular", 
                            "Spiral", "Wave", "Twinkle"]
        self.center_x = (word_clock.columns - 1) / 2
        self.center_y = (word_clock.rows - 1) / 2
    
    def kwheel(self, pos):
        """Fast color wheel - input 0-255, returns RGB tuple"""
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
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear display
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
                    k = int(distance * 15 + self.j) & 255
                    
                elif self.effect == 4:  # Spiral
                    dx = x - self.center_x
                    dy = y - self.center_y
                    angle = math.atan2(dy, dx)
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(angle * 40 + distance * 15 + self.j) & 255
                    
                elif self.effect == 5:  # Wave
                    wave = math.sin(x * 0.8 + self.j * 0.1) * 3
                    k = int(y * 25 + wave * 15 + self.j) & 255
                    
                elif self.effect == 6:  # Twinkle
                    # Simple hash for random but consistent twinkling
                    k = (x * 37 + y * 53 + self.j) & 255
                
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Overlay the time
        self.word_clock.update_clock()
        
        # Advance animation
        self.j = (self.j + 8) & 255  # Fast, simple increment
    
    def get_settings_template(self):
        """Return HTML for rainbow effect settings"""
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
