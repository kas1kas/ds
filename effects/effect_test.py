import time
from effects.base_effect import BaseEffect

class EffectTest(BaseEffect):
    name = "Test Effect"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.counter = 0
        self.last_update = 0
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < 0.5:  # Update every 0.5 seconds
            return
        
        self.last_update = current_time
        self.counter += 1
        
        # Simple pattern: cycle through colors
        color_index = self.counter % 3
        if color_index == 0:
            color = (255, 0, 0)  # Red
        elif color_index == 1:
            color = (0, 255, 0)  # Green
        else:
            color = (0, 0, 255)  # Blue
        
        self.word_clock.cls()
        # Light up first column
        for y in range(self.word_clock.rows):
            self.word_clock.setcolor_x_y(0, y, color)
        self.word_clock.update_clock()
