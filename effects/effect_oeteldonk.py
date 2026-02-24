import time
from effects.base_effect import BaseEffect

class EffectOeteldonk(BaseEffect):
    name = "Oeteldonk"
    description = "Oeteldonk theme"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.saved_color = None
        self.last_update = 0
    
    def draw(self):  # Change from update() to draw()
        current_time = time.time()
        if current_time - self.last_update < 60:  # Update every minute
            return
        
        self.last_update = current_time
        self.oeteldonk_background()
        # Set time color to cyan
        self.word_clock.letter_active_color = (0, 255, 255)
        self.word_clock.update_clock()
        # Restore original color for next time? Actually no, keep cyan for time
    
    def oeteldonk_background(self):
        for x in range(11):
            for y in range(10):
                if y > 6:
                    bgcolor = [169, 169, 0]
                elif y > 2:
                    bgcolor = [169, 169, 169]
                else:
                    bgcolor = [169, 0, 0]
                self.word_clock.setcolor_x_y(x, y, bgcolor)
