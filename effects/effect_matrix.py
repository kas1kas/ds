import random
import time
from matrix.base_effect import BaseEffect

class EffectMatrix(BaseEffect):
    name = "Matrix Rain"
    description = "Green rain with white time display"
    requires_time_update = True
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.drops = []  # Each drop: [column, row, speed, brightness, chars]
        self.last_update = 0
        self.update_interval = 0.1  # 100ms between updates
        self.matrix_green = (0, 255, 0)
        self.time_color = (255, 255, 255)  # White for time
        self.trail_length = 8  # How many LEDs per drop
        
    def start(self):
        """Initialize matrix rain"""
        # Store original colors
        self.orig_letter_color = self.word_clock.letter_active_color
        self.orig_dot_active = self.word_clock.dot_active_color
        
        # Set matrix colors
        self.word_clock.letter_active_color = self.time_color
        self.word_clock.dot_active_color = self.time_color
        
        # Create initial raindrops
        num_drops = self.word_clock.columns // 2  # One drop per 2 columns
        for _ in range(num_drops):
            self._create_drop()
    
    def stop(self):
        """Restore original colors"""
        self.word_clock.letter_active_color = self.orig_letter_color
        self.word_clock.dot_active_color = self.orig_dot_active
    
    def _create_drop(self):
        """Create a new raindrop"""
        col = random.randint(0, self.word_clock.columns - 1)
        # Start above the grid
        row = -random.randint(1, self.trail_length)
        speed = random.uniform(0.5, 2.0)
        drop = {
            'col': col,
            'row': row,
            'speed': speed,
            'brightness': random.uniform(0.3, 1.0),
            'active': True
        }
        self.drops.append(drop)
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear display (but keep background)
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                self.word_clock.setcolor_x_y(x, y, self.word_clock.background_color)
        
        # Update and draw drops
        for drop in self.drops[:]:  # Iterate over copy
            # Move drop
            drop['row'] += drop['speed'] * self.update_interval * 10
            
            # Draw trail
            for i in range(self.trail_length):
                y_pos = int(drop['row'] - i)
                if 0 <= y_pos < self.word_clock.rows:
                    # Calculate brightness (fade out with distance)
                    brightness_factor = max(0, 1.0 - (i / self.trail_length))
                    brightness = int(255 * drop['brightness'] * brightness_factor)
                    color = (0, brightness, 0)  # Green only
                    self.word_clock.setcolor_x_y(drop['col'], y_pos, color)
            
            # Remove drops that have fallen off
            if drop['row'] - self.trail_length > self.word_clock.rows:
                self.drops.remove(drop)
                # Create new drop to replace it
                self._create_drop()
        
        # Overlay the time (white letters)
        # Save and restore background colors for time display
        self.word_clock.update_clock()
        self.word_clock.strip.show()
    
    def get_settings_template(self):
        """Settings for matrix effect"""
        return '''
        <div class="matrix-settings">
            <label>Rain Speed:</label>
            <input type="range" id="matrix_speed" min="0.5" max="3.0" step="0.1" value="1.0">
            <label>Trail Length:</label>
            <input type="range" id="matrix_trail" min="3" max="15" step="1" value="8">
        </div>
        '''
