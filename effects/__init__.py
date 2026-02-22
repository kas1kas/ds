import os
import importlib
import inspect
import logging
from .base_effect import BaseEffect

logger = logging.getLogger(__name__)

def discover_effects(effects_dir=None):
    """Discover all effect classes in the effects directory"""
    if effects_dir is None:
        effects_dir = os.path.dirname(__file__)
    
    effects = {}
    
    # Scan all Python files in effects directory
    for filename in os.listdir(effects_dir):
        if filename.startswith('effect_') and filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove .py
            try:
                # Import the module
                module = importlib.import_module(f'effects.{module_name}')
                
                # Find all classes that inherit from BaseEffect
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseEffect) and obj != BaseEffect:
                        # Create instance without word_clock for now
                        effect_id = obj.__name__.lower().replace('effect', '')
                        effects[effect_id] = {
                            'class': obj,
                            'name': getattr(obj, 'name', name),
                            'description': getattr(obj, 'description', ''),
                            'module': module_name
                        }
                        logger.info(f"Discovered effect: {effect_id} - {obj.name}")
                        
            except Exception as e:
                logger.error(f"Failed to load effect module {module_name}: {e}")
    
    return effects

def load_effect(effect_id, word_clock, effects_info):
    """Instantiate an effect by ID"""
    if effect_id not in effects_info:
        return None
    
    effect_class = effects_info[effect_id]['class']
    return effect_class(word_clock)
