import time
from .base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
        self.first_update = True  # Add this flag
    
    def start(self):
        """Reset first_update flag when effect starts"""
        self.first_update = True
        self.last_minute = -1
    
    def update(self):
        current_minute = time.localtime().tm_min
        
        # Always show time on first update after switching
        if self.first_update:
            self.first_update = False
            self.last_minute = current_minute
            self.word_clock.cls()
            self.word_clock.update_clock()
        # Otherwise only update when minute changes
        elif current_minute != self.last_minute:
            self.last_minute = current_minute
            self.word_clock.cls()
            self.word_clock.update_clock()
    
    def get_settings_template(self):
        return "<div>Normal clock mode - no additional settings</div>"
