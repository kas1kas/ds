import time
from .base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
    
    def reset_timing(self):
        """Reset so next update shows time immediately"""
        self.last_minute = -1
    
    def update(self):
        current_minute = time.localtime().tm_min
        if current_minute != self.last_minute:
            self.last_minute = current_minute
            # Don't clear! The main program clears when needed
            self.word_clock.update_clock()
    
    def get_settings_template(self):
        return "<div>Normal clock mode - no additional settings</div>"
