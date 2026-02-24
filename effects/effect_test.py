import time
from effects.base_effect import BaseEffect

class EffectTest(BaseEffect):
    name = "Test Effect"
    
    def draw(self):
        """Simple test that should show something"""
        print("[TEST] Drawing")
        
        # Test 1: Just set a single red LED
        self.word_clock.cls()
        self.word_clock.setcolor_x_y(0, 0, (255, 0, 0))
        self.word_clock.strip.show()
        time.sleep(0.5)
        
        # Test 2: Try update_clock
        self.word_clock.cls()
        self.word_clock.update_clock()
        time.sleep(0.5)
        
        # Test 3: Both together
        self.word_clock.cls()
        self.word_clock.setcolor_x_y(5, 5, (0, 255, 0))
        self.word_clock.update_clock()
