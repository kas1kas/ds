import time
from .base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    description = "Standard word clock display"
    
    def __init__(self, word_clock):
        super().__init__(word_clock)
        self.last_minute = -1
    
    def draw(self):
        """Update when minute changes"""
        current_minute = time.localtime().tm_min
        if current_minute != self.last_minute:
            self.last_minute = current_minute
            self.word_clock.update_clock()  # This clears and shows time
    
    def get_settings_template(self):
        return "<div>Normal clock mode - no additional settings</div>"
