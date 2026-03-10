import time
from effects.base_effect import BaseEffect

class EffectGridTest(BaseEffect):
    name = "Grid Test"
    description = "Shows grid coordinates - X=red, Y=green, White at (0,0)"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        self.step = 0
        self.last_update = 0
        self.update_interval = 0.5
        
    def draw(self):
        current_time = time.time()
        
        if current_time - self.last_update < self.update_interval:
            return
            
        self.last_update = current_time
        
        # Clear all
        for x in range(16):
            for y in range(16):
                self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        
        if self.step == 0:
            # Show column 0 in red
            for y in range(16):
                self.word_clock.setcolor_x_y(0, y, (255, 0, 0))
            # Show row 0 in green
            for x in range(16):
                self.word_clock.setcolor_x_y(x, 0, (0, 255, 0))
            # Show (0,0) in white
            self.word_clock.setcolor_x_y(0, 0, (255, 255, 255))
            
        elif self.step == 1:
            # Show column 7 in red (middle)
            for y in range(16):
                self.word_clock.setcolor_x_y(7, y, (255, 0, 0))
            # Show row 7 in green (middle)
            for x in range(16):
                self.word_clock.setcolor_x_y(x, 7, (0, 255, 0))
            # Show (7,7) in white
            self.word_clock.setcolor_x_y(7, 7, (255, 255, 255))
            
        elif self.step == 2:
            # Show column 15 in red (last column)
            for y in range(16):
                self.word_clock.setcolor_x_y(15, y, (255, 0, 0))
            # Show row 15 in green (last row)
            for x in range(16):
                self.word_clock.setcolor_x_y(x, 15, (0, 255, 0))
            # Show (15,15) in white
            self.word_clock.setcolor_x_y(15, 15, (255, 255, 255))
        
        self.word_clock.update_clock()  # This will overlay the time
        self.step = (self.step + 1) % 3
