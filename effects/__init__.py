import os
import importlib
import inspect
import logging
from effects.base_effect import BaseEffect

logger = logging.getLogger(__name__)

def discover_effects():
    """Discover all effect classes in the effects directory and expand variants"""
    effects_dir = os.path.dirname(__file__)
    effects = {}
    
    for filename in os.listdir(effects_dir):
        if filename.startswith('effect_') and filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f'effects.{module_name}')
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseEffect) and obj != BaseEffect:
                        # Get variants from the class
                        variants = obj.get_variants()
                        for variant_id, variant_name in variants:
                            # Store the class and variant info
                            full_id = variant_id  # Could be something like "rainbow_diagonal"
                            effects[full_id] = {
                                'class': obj,
                                'name': variant_name,
                                'description': getattr(obj, 'description', ''),
                                'variant_id': variant_id,
                                'module': module_name
                            }
                            #logger.info(f"Discovered effect: {full_id} - {variant_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load effect module {module_name}: {e}")
    
    return effects
