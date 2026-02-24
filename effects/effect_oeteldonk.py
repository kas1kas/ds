import time
from effects.base_effect import BaseEffect

class EffectOeteldonk(BaseEffect):
    name = "Oeteldonk"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
    
    def draw(self):
        current_time = time.time()
        if current_time - self.last_update < 60:  # Update every minute
            return
        
        self.last_update = current_time
        
        # Draw Oeteldonk background colors
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                if y > 6:
                    color = (169, 169, 0)    # Yellow top
                elif y > 2:
                    color = (169, 169, 169)  # Grey middle
                else:
                    color = (169, 0, 0)      # Red bottom
                self.word_clock.setcolor_x_y(x, y, color)
        
        # Save original color, set time to cyan, then restore
        original_color = self.word_clock.letter_active_color
        self.word_clock.letter_active_color = (0, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
