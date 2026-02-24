import logging

class BaseEffect:
    """Base class for all effects"""
    
    name = "Base Effect"
    description = ""
    
    def __init__(self, word_clock):
        self.word_clock = word_clock
        self.logger = logging.getLogger(f"effect.{self.__class__.__name__}")
    
    def draw(self):
        """Draw one frame. Called every loop iteration."""
        pass
    
    def get_settings_template(self):
        """Return HTML for effect settings (optional)"""
        return ""
