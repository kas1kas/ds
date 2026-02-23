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
        self.frame_delay = 0.05
        self.effect = 0  # Sub-effect for rainbow variations
        self.effect_names = ["Diagonal", "Horizontal", "Vertical", "Circular", 
                            "Spiral", "Wave", "Twinkle"]
        self.center_x, self.center_y = 5, 4.5
        
    def kwheel(self, pos):
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
    
    def stop(self):
        self.logger.info(f"Stopping rainbow effect")
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_delay:
            return
        
        self.last_frame_time = current_time
        
        # Clear display
        self.word_clock.cls()
        
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                if self.effect == 0:  # Diagonal
                    k = (x * y + self.j) & 255
                elif self.effect == 1:  # Horizontal
                    k = (x + self.j) & 255
                elif self.effect == 2:  # Vertical
                    k = (y + self.j) & 255
                elif self.effect == 3:  # Circular
                    dx = x - self.center_x
                    dy = y - self.center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(distance * 10 + self.j) & 255
                elif self.effect == 4:  # Spiral
                    dx = x - self.center_x
                    dy = y - self.center_y
                    angle = math.atan2(dy, dx)
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(angle/math.pi * 128 + distance*5 + self.j) & 255
                elif self.effect == 5:  # Wave
                    wave = math.sin(x/2.0 + self.j/20.0) * 5
                    k = int(y + wave + self.j) & 255
                elif self.effect == 6:  # Twinkle
                    k = (x + y + self.j) & 255
                
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Show the time overlay
        self.word_clock.update_clock()
        self.j = (self.j + 1) % (256 * 5)
    
    def set_sub_effect(self, effect_num):
        if 0 <= effect_num < len(self.effect_names):
            self.effect = effect_num
            self.j = 0
            return True
        return False
    
    def get_settings_template(self):
        options = ''.join([f'<option value="{i}">{name}</option>' 
                          for i, name in enumerate(self.effect_names)])
        return f'''
        <div class="rainbow-settings">
            <label>Rainbow Pattern:</label>
            <select id="rainbow_pattern" onchange="setRainbowSubEffect(this.value)">
                {options}
            </select>
        </div>
        <script>
        function setRainbowSubEffect(value) {{
            fetch('/rainbow/set_effect', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{sub_effect: parseInt(value)}})
            }});
        }}
        </script>
        '''
