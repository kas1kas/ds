import logging

class BaseEffect:
    """Base class for all effects"""
    
    name = "Base Effect"
    description = ""
    
    @classmethod
    def get_variants(cls):
        """Return a list of (variant_id, variant_name) for this effect.
           By default, returns a single variant with the class's default id and name.
        """
        # Derive default id from class name (lowercase, remove 'effect' prefix)
        default_id = cls.__name__.lower().replace('effect', '')
        return [(default_id, cls.name)]
    
    def __init__(self, word_clock, variant_id=None):
        self.word_clock = word_clock
        self.logger = logging.getLogger(f"effect.{self.__class__.__name__}")
        self.variant_id = variant_id
    
    def get_dimensions(self):
        """Get the dimensions to use for effects based on config"""
        if hasattr(self.word_clock, 'effect_full_panel') and self.word_clock.effect_full_panel:
            # Use full panel dimensions (for effects that fill the screen)
            return 16, 16
        else:
            # Use clock area dimensions (for power saving)
            return self.word_clock.columns, self.word_clock.rows
    
    def clear_screen(self):
        """Clear the screen based on effect_full_panel setting"""
        if hasattr(self.word_clock, 'effect_full_panel') and self.word_clock.effect_full_panel:
            # Clear full panel
            for x in range(16):
                for y in range(16):
                    self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        else:
            # Clear only clock area
            self.word_clock.cls()  # Original cls method clears only clock area    
            
    def draw(self):
        """Draw one frame. Called every loop iteration."""
        pass
