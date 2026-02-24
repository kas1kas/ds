import time
from effects.base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
        self.first_draw = True  # Simple flag
    
    def draw(self):
        """Clear and show time"""
        current_minute = time.localtime().tm_min
        
        # Draw on first frame OR when minute changes
        if self.first_draw or current_minute != self.last_minute:
            self.first_draw = False
            self.last_minute = current_minute
            self.word_clock.cls()
            self.word_clock.update_clock()
