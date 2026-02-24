from effects.base_effect import BaseEffect
import time
import math
import random

class RainbowEffect(BaseEffect):
    def __init__(self, clock):
        super().__init__(clock)
        self.name = "Rainbow"
        self.description = "Rainbow animation with multiple patterns"
        self.j = 0
        self.sub_effect = 0  # 0: Diagonal, 1: Horizontal, 2: Vertical, 3: Circular, 4: Spiral, 5: Wave, 6: Twinkle
        self.last_update = 0
        self.update_interval = 0.03  # 30ms between updates (much faster than original)
        self.twinkle_pixels = []
        self.last_clock_update = 0
        self.clock_update_interval = 60  # Update clock display every 60 seconds
        
    def start(self):
        """Start the effect"""
        self.j = 0
        self.last_update = time.time()
        self.last_clock_update = time.time()
        # Pre-calculate twinkle pixels
        self.twinkle_pixels = [(random.randint(0, 10), random.randint(0, 9)) for _ in range(20)]
        
    def stop(self):
        """Stop the effect"""
        pass
        
    def update(self):
        """Update the effect"""
        current_time = time.time()
        
        # Control update rate
        if current_time - self.last_update < self.update_interval:
            return
            
        self.last_update = current_time
        
        # Update clock time occasionally (every minute)
        if current_time - self.last_clock_update >= self.clock_update_interval:
            self.clock.cls()
            self.clock.update_clock()
            self.last_clock_update = current_time
        
        # Clear the grid area (not the dots)
        for x in range(11):
            for y in range(10):
                self.clock.setcolor_x_y(x, y, (0, 0, 0))
        
        # Apply selected rainbow pattern
        center_x, center_y = 5, 4.5
        
        for x in range(11):
            for y in range(10):
                if self.sub_effect == 0:  # Diagonal
                    k = (x * y + self.j) & 255
                elif self.sub_effect == 1:  # Horizontal
                    k = (x + self.j) & 255
                elif self.sub_effect == 2:  # Vertical
                    k = (y + self.j) & 255
                elif self.sub_effect == 3:  # Circular ripple
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(distance * 10 + self.j) & 255
                elif self.sub_effect == 4:  # Spiral
                    dx = x - center_x
                    dy = y - center_y
                    angle = math.atan2(dy, dx)
                    distance = math.sqrt(dx*dx + dy*dy)
                    k = int(angle/math.pi * 128 + distance*5 + self.j) & 255
                elif self.sub_effect == 5:  # Wave
                    wave = math.sin(x/2.0 + self.j/10.0) * 3
                    k = int(y + wave + self.j) & 255
                elif self.sub_effect == 6:  # Twinkle - faster
                    # Update all pixels at once
                    if x == 0 and y == 0:
                        self.twinkle_pixels = [(random.randint(0, 10), random.randint(0, 9)) 
                                              for _ in range(15)]
                    if (x, y) in self.twinkle_pixels:
                        k = (x + y + self.j) & 255
                    else:
                        continue
                
                # Get color and set LED
                color = self.kwheel(k)
                self.clock.setcolor_x_y(x, y, color)
        
        # Update the display
        self.clock.strip.show()
        self.j = (self.j + 5) % (256 * 5)  # Faster increment
        
    def kwheel(self, pos):
        """Generate rainbow color"""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)
    
    def set_sub_effect(self, effect_num):
        """Set the sub-effect (0-6)"""
        try:
            effect_num = int(effect_num)
            if 0 <= effect_num <= 6:
                self.sub_effect = effect_num
                self.j = 0  # Reset animation
                return True
        except ValueError:
            pass
        return False
    
    def get_settings_template(self):
        """Return HTML for effect settings"""
        sub_effects = [
            "Diagonal", "Horizontal", "Vertical", "Circular",
            "Spiral", "Wave", "Twinkle"
        ]
        
        html = '''
        <div class="effect-settings">
            <h4>Rainbow Settings</h4>
            <label for="rainbow_sub_effect">Pattern:</label>
            <select id="rainbow_sub_effect" onchange="setRainbowSubEffect(this.value)">
        '''
        
        for i, name in enumerate(sub_effects):
            selected = "selected" if i == self.sub_effect else ""
            html += f'<option value="{i}" {selected}>{name}</option>'
        
        html += '''
            </select>
        </div>
        
        <script>
        function setRainbowSubEffect(effectNum) {
            fetch('/rainbow/set_effect', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sub_effect: effectNum})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('Rainbow sub-effect set to', effectNum);
                }
            })
            .catch(error => console.error('Error:', error));
        }
        </script>
        '''
        
        return html
