class EffectRandom(BaseEffect):
    def draw(self):
        # Draw random LEDs ON TOP of existing display
        for _ in range(20):
            x = random.randint(0, self.word_clock.columns - 1)
            y = random.randint(0, self.word_clock.rows - 1)
            color = self.word_clock.random_color(self.word_clock.rand_color)
            self.word_clock.setcolor_x_y(x, y, color)
        
        self.word_clock.update_clock()  # Draw time on top
