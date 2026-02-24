import time
from effects.base_effect import BaseEffect

class EffectTest(BaseEffect):
    name = "Test Effect"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.step = 0
        self.last_step_time = 0
        self.step_start_time = 0
    
    def draw(self):
        current_time = time.time()
        
        # Initialize step timing
        if self.step == 0:
            self.step = 1
            self.step_start_time = current_time
            self.last_step_time = current_time
            print("\n=== TEST EFFECT STARTED ===")
            return
        
        # Check if it's time for next step
        if current_time - self.step_start_time < 2:  # Show each step for 2 seconds
            return
            
        if self.step == 1:
            print("\n[TEST] Step 1: Single red LED at (0,0) - showing for 10 seconds")
            print("      You should see a RED LED at top-left corner")
            self.word_clock.cls()
            self.word_clock.setcolor_x_y(0, 0, (255, 0, 0))
            self.word_clock.strip.show()
            self.step_start_time = current_time
            self.step = 2
            
        elif self.step == 2:
            print("\n[TEST] Step 2: Just time display - showing for 10 seconds")
            print("      You should see the current time in white")
            self.word_clock.cls()
            self.word_clock.update_clock()
            self.step_start_time = current_time
            self.step = 3
            
        elif self.step == 3:
            print("\n[TEST] Step 3: Green LED at dot position + time - showing for 10 seconds")
            print("      You should see a GREEN dot (minute dot) AND the time")
            self.word_clock.cls()
            # Set green LED at first minute dot (should persist)
            first_dot = list(self.word_clock.minute_dots.values())[0]
            self.word_clock.set_led_color(first_dot, (0, 255, 0))
            self.word_clock.update_clock()
            self.step_start_time = current_time
            self.step = 4
            
        elif self.step == 4:
            print("\n[TEST] Step 4: Green LED in word area + time - showing for 10 seconds")
            print("      The GREEN LED should be CLEARED (only time visible)")
            self.word_clock.cls()
            # Set green LED in word area (should be cleared by update_clock)
            self.word_clock.setcolor_x_y(5, 5, (0, 255, 0))
            self.word_clock.update_clock()
            self.step_start_time = current_time
            self.step = 5
            
        elif self.step == 5:
            print("\n[TEST] Step 5: Multiple random LEDs + time - showing for 15 seconds")
            print("      You should see YELLOW LEDs scattered AND the time")
            self.word_clock.cls()
            # Set 30 random LEDs
            import random
            for _ in range(30):
                x = random.randint(0, self.word_clock.columns - 1)
                y = random.randint(0, self.word_clock.rows - 1)
                self.word_clock.setcolor_x_y(x, y, (255, 255, 0))
            self.word_clock.update_clock()
            self.step_start_time = current_time
            self.step = 6
            
        elif self.step == 6:
            print("\n[TEST] Test complete! Returning to normal mode...")
            print("=====================================")
            # Switch back to normal effect
            self.word_clock.set_effect("normal")
