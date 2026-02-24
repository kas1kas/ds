import random
import time
from effects.base_effect import BaseEffect

class EffectTestRandom(BaseEffect):
    name = "TestRandom"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = 0.02
        self.frame_count = 0
        print(f"[RANDOM] Initialized with columns={word_clock.columns}, rows={word_clock.rows}")
        
    def draw(self):
        self.frame_count += 1
        current_time = time.time()
        
        # Print every 30 frames (about once per second at 50fps)
        if self.frame_count % 30 == 0:
            print(f"[RANDOM] Drawing frame {self.frame_count}, time since last: {current_time - self.last_update:.3f}s")
        
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Clear the display
        self.word_clock.cls()
        
        # Try a simple test pattern first to verify drawing works
        # Set a single red LED at (0,0) every frame
        if self.frame_count < 100:  # First 100 frames
            self.word_clock.setcolor_x_y(0, 0, (255, 0, 0))
            print(f"[RANDOM] Set test LED at (0,0) to RED")
        
        # Then do the random LEDs
        num_leds = random.randint(20, 30)
        for i in range(num_leds):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            
            # Get color from word_clock
            color = self.word_clock.random_color(self.word_clock.rand_color)
            
            # Print first few random LEDs
            if i < 3 and self.frame_count < 10:
                print(f"[RANDOM] LED {i}: ({x},{y}) -> {color}")
            
            self.word_clock.setcolor_x_y(x, y, color)
        
        # Show the time overlay
        self.word_clock.update_clock()
