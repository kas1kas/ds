class EffectNormal(BaseEffect):
    def draw(self):
        self.word_clock.cls()           # Clear first
        self.word_clock.update_clock()  # Then draw time
