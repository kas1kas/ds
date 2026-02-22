from .base_effect import BaseEffect

class EffectNormal(BaseEffect):
    name = "Normal Clock"
    description = "Standard word clock display"
    
    def update(self):
        self.word_clock.cls()
        self.word_clock.update_clock()
