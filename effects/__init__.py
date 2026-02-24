import os
import importlib
import inspect
import logging
from effects.base_effect import BaseEffect  # Absolute import

logger = logging.getLogger(__name__)

def discover_effects():
    """Discover all effect classes in the effects directory"""
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
                        # Create effect ID from filename (remove 'effect_' prefix)
                        effect_id = module_name[7:]  # Remove 'effect_' prefix
                        effects[effect_id] = {
                            'class': obj,
                            'name': getattr(obj, 'name', name),
                            'description': getattr(obj, 'description', ''),
                            'module': module_name
                        }
                        #logger.info(f"Discovered effect: {effect_id} - {obj.name}")
                        
            except Exception as e:
                logger.error(f"__INIT_.py: Failed to load effect module {module_name}: {e}")
    
    return effects
