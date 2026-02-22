import math
import random
import time
from .base_effect import BaseEffect

class EffectRainbow(BaseEffect):
    name = "Rainbow"
    description = "Animated rainbow patterns"
    requires_time_update = False
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.j = 0
        self.last_frame_time = 0
        self.frame_delay = 0.01
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
    
    def set_effect(self, effect_num):
        if 0 <= effect_num < len(self.effect_names):
            self.effect = effect_num
            self.j = 0
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_delay:
            return
        
        self.last_frame_time = current_time
        
        for x in range(11):
            for y in range(10):
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
                    if x == 0 and y == 0:
                        self._update_twinkle()
                    continue
                
                color = self.kwheel(k)
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Show time overlay if needed (optional)
        self.word_clock.update_clock()
        self.word_clock.strip.show()
        self.j = (self.j + 1) % (256 * 5)
    
    def _update_twinkle(self):
        for _ in range(10):
            x = random.randint(0, 10)
            y = random.randint(0, 9)
            k = (x + y + self.j) & 255
            color = self.kwheel(k)
            self.word_clock.setcolor_x_y(x, y, color)
    
    def get_settings_template(self):
        """Return HTML for rainbow effect settings"""
        options = ''.join([f'<option value="{i}">{name}</option>' 
                          for i, name in enumerate(self.effect_names)])
        return f'''
        <div class="rainbow-settings">
            <label>Rainbow Pattern:</label>
            <select id="rainbow_pattern" onchange="setRainbowEffect(this.value)">
                {options}
            </select>
        </div>
        '''
