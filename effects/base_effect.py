from abc import ABC, abstractmethod
import logging

class BaseEffect(ABC):
    """Base class for all word clock effects"""
    
    def __init__(self, word_clock):
        self.word_clock = word_clock
        self.name = "Base Effect"
        self.description = ""
        self.requires_time_update = True  # Does effect need time display?
        self.logger = logging.getLogger(f"effect.{self.__class__.__name__}")
    
    @abstractmethod
    def update(self):
        """Update the display - called every loop iteration"""
        pass
    
    def start(self):
        """Called when effect is activated"""
        self.logger.info(f"Starting effect: {self.name}")
        pass
    
    def stop(self):
        """Called when effect is deactivated"""
        self.logger.info(f"Stopping effect: {self.name}")
        pass
    
    def on_time_change(self):
        """Called when time changes (every minute)"""
        pass
    
    def get_settings_template(self):
        """Return HTML for effect-specific settings (optional)"""
        return ""
    
    def process_settings(self, form_data):
        """Process effect-specific settings from web interface"""
        pass
    
    @property
    def id(self):
        """Return unique ID for this effect"""
        return self.__class__.__name__.lower().replace('effect', '')
