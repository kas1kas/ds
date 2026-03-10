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
        """Get the dimensions to use for effects based on config
           Returns:
             - When effect_full_panel True: (16, 16) for full panel
             - When effect_full_panel False: (11, 10) for clock area
        """
        if hasattr(self.word_clock, 'effect_full_panel') and self.word_clock.effect_full_panel:
            # Full panel mode - effects use entire 16x16 panel
            return 16, 16
        else:
            # Power saving mode - effects only use 11x10 clock area
            return 11, 10
        
    def map_coordinates(self, x, y):
        """Map logical coordinates to physical coordinates based on panel wiring"""
        if (hasattr(self.word_clock, 'grid') and self.word_clock.grid == "16" and 
            hasattr(self.word_clock, 'effect_full_panel') and self.word_clock.effect_full_panel):
            # For full 16x16 panel, adjust Y based on column parity
            if x % 2 == 0:
                # Even columns: physical Y is inverted
                max_rows = 16
                return x, max_rows - 1 - y
            return x, y

    def clear_screen(self):
        """Clear the screen based on effect_full_panel setting"""
        if hasattr(self.word_clock, 'effect_full_panel') and self.word_clock.effect_full_panel:
            # Clear full panel
            for x in range(self.word_clock.panel_columns):
                for y in range(self.word_clock.panel_rows):
                    self.word_clock.setcolor_x_y(x, y, (0, 0, 0))
        else:
            # Clear only clock area
            self.word_clock.cls()  # Original cls method clears only clock area        
            
    def draw(self):
        """Draw one frame. Called every loop iteration."""
        pass
