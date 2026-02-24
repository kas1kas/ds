import time
from effects.base_effect import BaseEffect  # Change to absolute import

class EffectDark(BaseEffect):
    name = "Dark Mode"
    description = "Only minute dots"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_update = 0
        self.light_interval = getattr(word_clock, 'light_interval', 1)
    
    def draw(self):  # Change from start() to draw()
        current_time = time.time()
        if current_time - self.last_update < self.light_interval:
            return
        
        self.last_update = current_time
        self.word_clock.cls()
        self.word_clock.next_minuteled()
        self.word_clock.strip.show()
