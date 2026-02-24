import random
import time
from effects.base_effect import BaseEffect

class EffectMatrix2(BaseEffect):
    name = "Matrix2"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.drops = []
        self.last_update = 0
        self.update_interval = 0.1  # 100ms for animation speed
        
        # Initialize drops
        for _ in range(20):
            self._create_drop()
    
    def _create_drop(self):
        x = random.randint(0, self.word_clock.columns - 1)
        y = random.randint(-10, 0)
        speed = random.uniform(0.5, 2.0)
        self.drops.append([x, y, speed])
    
    def draw(self):
        current_time = time.time()
        
        # Control animation speed, but ALWAYS draw something
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            # Move drops
            for drop in self.drops:
                drop[1] += drop[2] * 0.5
                if drop[1] > self.word_clock.rows + 5:
                    drop[1] = -random.randint(5, 15)
                    drop[2] = random.uniform(0.5, 2.0)
        
        # Clear grid
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        
        # Draw drops at current positions
        for drop in self.drops:
            x, y, _ = drop
            for i in range(5):  # Trail
                trail_y = int(y - i)
                if 0 <= trail_y < self.word_clock.rows:
                    brightness = max(0, 255 - i * 50)
                    self.word_clock.setcolor_x_y(x, trail_y, (0, brightness, 0))
        
        # Draw time in white
        original_color = self.word_clock.letter_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
