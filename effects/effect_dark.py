import time
from effects.base_effect import BaseEffect

class EffectDark(BaseEffect):
    name = "Dark Mode"
    
    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock)
        self.last_update = 0
        self.update_interval = getattr(word_clock, 'light_interval', 1)
    
    def draw(self):
        """Only show moving minute dot"""
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        self.word_clock.cls()                    # Clear everything
        self.word_clock.next_minuteled()         # Update moving dot
        self.word_clock.strip.show()              # Show just the dot
