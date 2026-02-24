__version__ = "7.13"
# Woordklok - Simple plugin version
# 
import argparse
import json
import logging
import time
import datetime
import os
import random
import bisect
import math
from rpi_ws281x import PixelStrip, Color
from python_tsl2591 import tsl2591
import smbus2
from smbus2 import SMBus
from flask import Flask, request, render_template, jsonify, send_file

# Import effect system
from effects import discover_effects

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
app = Flask(__name__, template_folder='templates_plugin')

# BH1750 Sensor Implementation
class BH1750:
    # Define some constants from the datasheet
    POWER_DOWN = 0x00
    POWER_ON = 0x01
    RESET = 0x07
    CONTINUOUS_HIGH_RES_MODE = 0x10
    CONTINUOUS_HIGH_RES_MODE_2 = 0x11
    CONTINUOUS_LOW_RES_MODE = 0x13
    ONE_TIME_HIGH_RES_MODE = 0x20
    ONE_TIME_HIGH_RES_MODE_2 = 0x21
    ONE_TIME_LOW_RES_MODE = 0x23

    def __init__(self, bus=1, address=0x23):
        self.bus = SMBus(bus)
        self.address = address

    def _set_mode(self, mode):
        self.bus.write_byte(self.address, mode)

    def reset(self):
        self._set_mode(self.RESET)

    def power_down(self):
        self._set_mode(self.POWER_DOWN)

    def power_on(self):
        self._set_mode(self.POWER_ON)

    def measure_high_res(self, mode=CONTINUOUS_HIGH_RES_MODE):
        """Measure luminosity in lux with high resolution"""
        self._set_mode(mode)
        time.sleep(0.180 if mode == self.CONTINUOUS_HIGH_RES_MODE_2 else 0.120)
        data = self.bus.read_i2c_block_data(self.address, mode, 2)
        return (data[0] << 8 | data[1]) / 1.2

class LanguageSettings:
    def __init__(self, config, language, grid_size):
        self.config = config
        self.language = language
        self.grid_size = grid_size
        self.load_language_settings()
        
    def load_language_settings(self):
        self.it_is = self.config["IT_IS"].get(self.language, {})
        self.minute_blocks = self.config["MINUTE_BLOCKS"].get(self.language, {})
        self.words = self.config["WORDS"].get(self.language, {}).get(str(self.grid_size), {})
        self.min_block_check = self.config["MIN_BLOCK_CHECK"].get(self.language, {})
        self.hour_words = self.config["HOUR_WORDS"].get(self.language, {})
        
    def update_language(self, new_language):
        if new_language in ["NL", "EN"]:
            self.language = new_language
            self.load_language_settings()
            return True
        return False

class WordClock:
    def __init__(self, config):
        self.version = __version__
        self.purist = config["PURIST"]
        self.calibrate = config["CALIBRATE"]
        self.woordklok = config["WOORDKLOK"]
        self.grid = config["GRID"]
        self.light_interval = config["LIGHT_INTERVAL"]
        self.language_settings = LanguageSettings(config, config["LANGUAGE"], self.grid)
        self.led_pin = 18
        self.led_freq_hz = 800000
        self.led_dma = 10
        self.led_channel = 0
        self.def_brightness = config["DEF_BRIGHTNESS"]
        self.background_color = config["BACKGROUND_COLOR"]
        self.letter_active_color = config["LETTER_ACTIVE_COLOR"]
        self.dot_active_color = config["DOT_ACTIVE_COLOR"]
        self.dot_inactive_color = config["DOT_INACTIVE_COLOR"]
        self.minute_dots = config["MINUTE_DOTS"].get(str(self.grid), {}) 
        self.dot_order = ["MLT", "MLB", "MRB", "MRT"]     # Fixed cycling order
        self.current_dot_index = 0                        # Initialize cycling position
        self.dot_dark_color = config["DOT_DARK_COLOR"]       
        self.clock_type = config["CLOCK_TYPE"]            # For backward compatibility
        self.rand_color = config["RAND_COLOR"]
        self.lut_in =  config.get("LUT_IN")
        self.lut_out=  config.get("LUT_OUT") 
        self.current_mode = "normal"  # 'normal' or 'calibration'
        self.auto_brightness_enabled = True
        self.light_sensor_type = "none"                   # default before autodetect
        
        if self.grid=="16":
          self.led_count = 256
          self.columns = 16
          self.rows = 16
        else:
          self.led_count = 114
          self.columns = 11
          self.rows = 10

        # Initialize LED strip
        self.initialize_led()
        self.initialize_lightsensor()
        
        # Load effects - simple dictionary of effect instances
        self.effects = {}
        self.current_effect_id = "normal"  # Default
        
        # Discover and create all effects
        #extra logging
        effects_info = discover_effects()
        logging.info(f"Discovered effects: {list(effects_info.keys())}")

        for effect_id, info in effects_info.items():
            try:
                effect_class = info['class']
                logging.info(f"Creating effect: {effect_id} with class {effect_class.__name__}")
                self.effects[effect_id] = effect_class(self)
                logging.info(f"✓ Successfully loaded effect: {effect_id} - {self.effects[effect_id].name}")
            except Exception as e:
                logging.error(f"✗ Failed to load effect {effect_id}: {e}")
                import traceback
                traceback.print_exc()

        logging.info(f"=== END EFFECT DISCOVERY ===")
        logging.info(f"Total effects loaded: {len(self.effects)}")
                
        # Set initial effect
        if "DEFAULT_EFFECT" in config:
            self.current_effect_id = config["DEFAULT_EFFECT"]
        elif self.current_effect_id in self.effects:
            pass  # Keep default
        else:
            # Find first available effect
            self.current_effect_id = next(iter(self.effects.keys()), "normal")
        
        logging.info(f"Design   : Woosh") 
        logging.info(f"Made by  : GraWoosh Labs") 
        logging.info(f"Woordklok: {self.woordklok}")
        logging.info(f"version  : {self.version}")
        logging.info(f"Effect   : {self.current_effect_id}") 
        logging.info(f"Random   : {self.rand_color}") 
        logging.info(f"Language : {self.language_settings.language}")
        logging.info(f"Grid     : {self.grid}") 
        logging.info(f"Lut In   : {self.lut_in}")
        logging.info(f"Lut Out  : {self.lut_out}")
        logging.info(f"Loaded   : {len(self.effects)} effects")
   
    def initialize_led(self):
        try:
            self.strip = PixelStrip(
                self.led_count, self.led_pin, self.led_freq_hz,
                self.led_dma, False, 100, self.led_channel
            )
            self.strip.begin()
            self.strip.setBrightness(self.def_brightness)
            logging.info("LED strip initialized.")
        except Exception as e:
            logging.error(f"Failed to initialize LED strip: {e}")
            exit(1)

    def initialize_lightsensor(self):        
        BH1750_ADDRESS = 0x23  # Can also be 0x5C for some BH1750 variants
        TSL2591_ADDRESS = 0x29
        
        bus = smbus2.SMBus(1)  # 1 indicates /dev/i2c-1
        
        try:
            try:
                # BH1750 power on command
                bus.write_byte(BH1750_ADDRESS, 0x01)
                time.sleep(0.1)
                # Try to read (continuous high res mode)
                bus.write_byte(BH1750_ADDRESS, 0x10)
                time.sleep(0.1)
                data = bus.read_i2c_block_data(BH1750_ADDRESS, 0x10, 2)
                self.light_sensor = BH1750()
                self.light_sensor_type = "BH1750"
                logging.info("BH1750 light sensor detected and initialized.")
                return "BH1750"
            except (IOError, OSError):
                pass
            
            try:
                # Read TSL2591 ID register (should return 0x50)
                bus.write_byte(TSL2591_ADDRESS, 0xB2)  # 0xB2 is command bit + ID register
                id_reg = bus.read_byte(TSL2591_ADDRESS)
                if id_reg == 0x50:
                    self.light_sensor = tsl2591()
                    self.light_sensor_type = "TSL2591"
                    logging.info("TSL2591 light sensor detected and initialized.")
                    return "TSL2591"
            except (IOError, OSError):
                pass
            
            self.light_sensor = "none"
            self.light_sensor_type = "none"
            self.calibrate = False
            logging.warning("No light sensor detected")
            logging.info(f"Default brightness: {self.def_brightness}")
            return "No light sensor detected"
        
        finally:
            bus.close()

    def update_language(self, new_language):
        return self.language_settings.update_language(new_language)

    def set_effect(self, effect_id):
        """Switch to a different effect"""
        if effect_id in self.effects:
            self.current_effect_id = effect_id
            # Clear the display when switching
            self.cls()
            self.strip.show()
        
            # Force an immediate draw of the new effect
            current_effect = self.effects.get(effect_id)
            if current_effect:
                current_effect.draw()
        
            logging.info(f"Switched to effect: {effect_id}")
            return True
        return False

    def set_mode(self, mode):
        """Set the current operation mode"""
        self.current_mode = mode
        if mode == "calibration":
            # Store original brightness when entering calibration
            self.original_brightness = self.strip.getBrightness()
            # Disable auto-brightness updates
            self.auto_brightness_enabled = False
        else:
            # Restore auto-brightness in normal mode
            self.auto_brightness_enabled = True
            self.update_brightness()
        
    def next_minuteled(self):
        # Turn off previous LED
        prev_dot = self.dot_order[(self.current_dot_index - 1) % 4]
        self.set_led_color(self.minute_dots[prev_dot], (0, 0, 0))
              
        # Turn on current LED
        current_dot = self.dot_order[self.current_dot_index]
        self.set_led_color(self.minute_dots[current_dot], self.dot_dark_color)
              
        # Advance to next LED
        self.current_dot_index = (self.current_dot_index + 1) % 4

    def set_led_color(self, led_index, color):
        if 0 <= led_index < self.led_count:
            self.strip.setPixelColor(led_index, Color(color[0], color[1], color[2]))

    def map_grid_to_led(self, grid_index):
        if self.grid == "16":                              #16x16 grid
           grd = grid_index + 34 + 5 * (grid_index // 11) 
           col = grd % 16                                  # Column (0-10)
           row = grd // 16                                 # Row (0-15, top to bottom)
           if col % 2 == 0:                                # even columns: bottom to top
               led_index = (col * 16) + (15 - 1 - row)
           else:                                           # odd columns: top to bottom
               led_index = (col * 16) + row + 1
           return led_index
        else:
                                                           # For 11x10 grid
            col = grid_index % self.columns
            row = grid_index // self.columns
            if col % 2 == 0:                               # Even columns: top to bottom
                led_index = 2 + (col * self.rows) + row    # rows = 10
            else:                                          # Odd columns: bottom to top
                led_index = 2 + (col * self.rows) + (self.rows - 1 - row)
            return led_index
    
    def update_brightness(self):
        if not self.auto_brightness_enabled or self.light_sensor_type == "none":
            return

        try:
            if self.light_sensor_type == "BH1750":
                lux = self.light_sensor.measure_high_res()
            else:
                light_data = self.light_sensor.get_current()
                lux = abs(light_data['lux'])
        
            # Smooth interpolation between calibration points
            if len(self.lut_in) >= 2:
                # Find the segment where lux falls
                idx = bisect.bisect_left(self.lut_in, lux) - 1
                idx = max(0, min(idx, len(self.lut_in) - 2))
            
                # Linear interpolation
                x0, x1 = self.lut_in[idx], self.lut_in[idx+1]
                y0, y1 = self.lut_out[idx], self.lut_out[idx+1]
            
                if x1 != x0:  # Avoid division by zero
                    brightness = y0 + (y1 - y0) * (lux - x0) / (x1 - x0)
                else:
                    brightness = y0
            else:
                # Fallback to simple mapping if not enough calibration points
                brightness = self.lut_out[0] if lux < self.lut_in[0] else self.lut_out[-1]
        
            # Apply exponential smoothing
            if hasattr(self, 'last_brightness'):
                alpha = 0.3  # Smoothing factor
                brightness = alpha * self.last_brightness + (1 - alpha) * brightness
            self.last_brightness = brightness
            self.strip.setBrightness(int(brightness))
            
        except Exception as e:
            logging.error(f"Failed to update brightness: {e}")

    def activate_word(self, word):
        if word in self.language_settings.words:
            start, end = self.language_settings.words[word]
            for i in range(start, end + 1):
                led_index = self.map_grid_to_led(i)
                if led_index != -1:
                    self.set_led_color(led_index, self.letter_active_color)
   
    def update_clock(self):
        """Draw current time """
        
        now = time.localtime()
        hours = now.tm_hour % 12 or 12
        minutes = now.tm_min
        
        # Set minute dots
        minute_dots = minutes % 5
        for dot, index in self.minute_dots.items():
            self.set_led_color(index, self.dot_active_color \
                  if minute_dots >= list(self.minute_dots.keys()).index(dot) + 1 else self.dot_inactive_color)
        
        # Determine minute phrase and hour
        minute_block = minutes // 5
        adjusted_hours = hours    
        
        # Show "IT IS"
        if not self.purist:
            for word in self.language_settings.it_is:
                self.activate_word(word)
        
        # Adjust hour per language minutes
        if minute_block >= self.language_settings.min_block_check:
            adjusted_hours = (hours % 12) + 1
            if adjusted_hours == 13:
                adjusted_hours = 1
        
        # Activate words based on minute block
        if str(minute_block) in self.language_settings.minute_blocks:
            for word in self.language_settings.minute_blocks[str(minute_block)]:
                self.activate_word(word)
            self.activate_word(self.language_settings.hour_words[adjusted_hours - 1])
        
        self.strip.show()

    def set_random_led(self, tint):
        """Set a random LED with tint"""
        self.setcolor_x_y(random.randint(0, self.columns-1), 
                         random.randint(0, self.rows-1), 
                         self.random_color(tint))
       
    def random_color(self, tint):
        """Generate random color based on tint from config"""
        if tint == "blue":
            r = random.randint(29, 69)
            g = random.randint(31, 71)
            b = random.randint(105, 245)
        elif tint == "orange":
            r = random.randint(100, 155)
            g = random.randint(20, 40)
            b = random.randint(0, 2)
        elif tint == "red":
            r = random.randint(200, 255)
            g = random.randint(0, 50)
            b = random.randint(0, 50)
        elif tint == "green":
            r = random.randint(0, 50)
            g = random.randint(200, 255)
            b = random.randint(0, 50)
        elif tint == "purple":
            r = random.randint(150, 255)
            g = random.randint(0, 50)
            b = random.randint(150, 255)
        else:  # full random
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
        return (r, g, b) 
      
    def cls(self):
        """Clear all LEDs to background color"""
        for i in range(self.led_count):
            self.set_led_color(i, self.background_color)

    def setcolor_x_y(self, x, y, color):
        """Set LED color by grid coordinates"""
        if x < 0 or x >= self.columns or y < 0 or y >= self.rows:
            return
            
        if self.grid == "16":
            adjusted_x = x + 2  # Skip the first two columns
            adjusted_y = y + 3  # and first three rows
            if adjusted_x % 2 == 0:  # Even columns: top to bottom
                led_index = (adjusted_x * 16) + adjusted_y
            else:  # Odd columns: bottom to top
                led_index = (adjusted_x * 16) + (15 - adjusted_y)
        else:  # For 11x10 grid
            if x % 2 == 0:  # Even columns: top to bottom
                led_index = 2 + (x * 10) + y
            else:  # Odd columns: bottom to top
                led_index = 2 + (x * 10) + (9 - y)
        self.set_led_color(led_index, color)
    
    # End Subs ------------------------------------------------------------------------------

# Merge configs before creating the instance
def load_merged_config():
    """
    Load and merge system config (from git) with user config (preserved)
    User settings in config_loc.json override system defaults in config_gen.json
    """
    script_dir = '/home/pi/ds'
    user_config_dir = '/home/pi/.wordclock'
    
    # Paths
    system_config_path = os.path.join(script_dir, 'config_gen.json')
    user_config_path = os.path.join(user_config_dir, 'config_loc.json')
    
    try:
        # Load system config (this gets updated with git pull)
        with open(system_config_path) as f:
            config_gen = json.load(f)
        logging.info(f"Loaded system config from {system_config_path}")
        
        # Load user config if it exists (preserved across updates)
        if os.path.exists(user_config_path):
            with open(user_config_path) as f:
                config_loc = json.load(f)
            logging.info(f"Loaded user config from {user_config_path}")
        else:
            config_loc = {}
            logging.warning(f"No user config found at {user_config_path}, using defaults only")
        
        # MERGE: user settings override system defaults
        merged_config = {**config_gen, **config_loc}
        
        # Log what was merged
        overridden_keys = set(config_loc.keys()) & set(config_gen.keys())
        if overridden_keys:
            logging.info(f"User settings overriding system defaults for: {overridden_keys}")
        
        return merged_config
        
    except FileNotFoundError as e:
        logging.error(f"Required config file not found: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading config: {e}")
        return None
        
# Initialize word clock
config = load_merged_config()
word_clock = WordClock(config)

# Import web routes (must be after word_clock is created)
import web_routes

# Main function to run the word clock
# In run_clock function, add frame counter:

def run_clock():
    last_brightness_update = time.time()
    last_frame_time = time.time()
    frame_delay = 0.01
    
    try:
        while True:
            current_time = time.time()
                       
            # Update brightness
            if current_time - last_brightness_update >= word_clock.light_interval:
                word_clock.update_brightness()
                last_brightness_update = current_time
            
            # Get current effect and draw
            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect:
                current_effect.draw()
                
            time.sleep(frame_delay)
            
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        word_clock.cls()
        word_clock.strip.show()

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=80))
    flask_thread.daemon = True
    flask_thread.start()

    # Run the word clock
    run_clock()
