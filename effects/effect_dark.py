class EffectDark(BaseEffect):
    def draw(self):
        self.word_clock.cls()                    # Clear everything
        self.word_clock.next_minuteled()         # Update dot
        # Don't call update_clock() - no time display
