import time
from effects.base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
        self.first_draw = True
        print("[NORMAL] Initialized")
    
    def draw(self):
        print(f"[NORMAL] draw() called, first_draw={self.first_draw}")
        current_minute = time.localtime().tm_min
        print(f"[NORMAL] current_minute={current_minute}, last_minute={self.last_minute}")
        
        if self.first_draw or current_minute != self.last_minute:
            print(f"[NORMAL] Drawing! first_draw={self.first_draw}")
            self.first_draw = False
            self.last_minute = current_minute
            self.word_clock.cls()
            self.word_clock.update_clock()
        else:
            print("[NORMAL] No change, skipping")
