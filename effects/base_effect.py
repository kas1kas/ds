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
    
    def draw(self):
        """Draw one frame. Called every loop iteration."""
        pass
