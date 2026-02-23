__version__ = "7.02"
# Woordklok
# updating to effects plugin version
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
from effects import discover_effects, load_effect
from effects.base_effect import BaseEffect

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
        self.clock_type = config["CLOCK_TYPE"]
        self.rand_color = config["RAND_COLOR"]
        self.lut_in =  config.get("LUT_IN")
        self.lut_out=  config.get("LUT_OUT") 
        self.CURSOR_UP = "\x1b[2A"
        self.current_mode = "normal"  # 'normal' or 'calibration'
        self.auto_brightness_enabled = True
        self.light_sensor_type = "none"                   # default before autodetect
                
        if self.grid=="16":
          self.led_count = 256
          self.columns =16
          self.rows=16
        else:
          self.led_count = 114
          self.columns = 11
          self.rows = 10

        # Effect system
        self.current_effect_id = "normal"
        self.effects_info = discover_effects()
        self.effects = {}  # Will store instantiated effects
        self.current_effect = None
        
        # Load available effects into config
        self.available_effects = [
            {'id': eid, 'name': info['name'], 'description': info['description']}
            for eid, info in self.effects_info.items()
        ]  
        
        # Instantiate all effects (or lazy-load them)
        self._load_effect("normal")  # Load default effect
        
        logging.info(f"Design   : Woosh") 
        logging.info(f"Made by  : GraWoosh Labs") 
        logging.info(f"Woordklok: {self.woordklok}")
        logging.info(f"version  : {self.version}")
        logging.info(f"Clock    : {self.clock_type}") 
        logging.info(f"Random   : {self.rand_color}") 
        logging.info(f"Language : {self.language_settings.language}")
        logging.info(f"Grid     : {self.grid}") 
        logging.info(f"Lut In   : {self.lut_in}")
        logging.info(f"Lut Out  : {self.lut_out}")
        logging.info(f"Loaded   : {len(self.effects_info)} effects")
        
        self.initialize_led()
        self.initialize_lightsensor()
   
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
    
    def cls(self):
        for i in range(self.led_count):
           self.set_led_color(i, self.background_color)
        
    def _load_effect(self, effect_id):
        """Load and instantiate an effect"""
        if effect_id in self.effects:
            return self.effects[effect_id]
        
        effect = load_effect(effect_id, self, self.effects_info)
        if effect:
            self.effects[effect_id] = effect
            return effect
        return None
    
    def set_effect(self, effect_id):
        """Switch to a different effect"""
        if effect_id not in self.effects_info:
            logging.error(f"Unknown effect: {effect_id}")
            return False
        
        # Stop current effect
        if self.current_effect:
            self.current_effect.stop()
        
        # Load and start new effect
        new_effect = self._load_effect(effect_id)
        if new_effect:
            self.current_effect = new_effect
            self.current_effect_id = effect_id
            new_effect.start()
            logging.info(f"Switched to effect: {new_effect.name}")
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
        
            # Apply exponential smoothing (optional, makes transitions smoother)
            if hasattr(self, 'last_brightness'):
                alpha = 0.3  # Smoothing factor (0-1, higher = more smoothing)
                brightness = alpha * self.last_brightness + (1 - alpha) * brightness
            self.last_brightness = brightness
            self.strip.setBrightness(int(brightness))
            
            #logging.info(f"lux, bright: {self.light_sensor_type}, {self.auto_brightness_enabled}, {lux}, {brightness}")
            
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
        now = time.localtime()
        hours = now.tm_hour % 12 or 12
        minutes = now.tm_min
        # -------------------------------------------------Set minute dots
        minute_dots = minutes % 5
        for dot, index in self.minute_dots.items():
            self.set_led_color(index, self.dot_active_color \
                  if minute_dots >= list(self.minute_dots.keys()).index(dot) + 1 else self.dot_inactive_color)
        # -------------------------------------------------Determine minute phrase and hour
        minute_block = minutes // 5
        adjusted_hours = hours    
        # -------------------------------------------------Show "IT IS"
        if not self.purist:
            for word in self.language_settings.it_is:
                self.activate_word(word)
        # -------------------------------------------------Adjust hour per language minutes
        if minute_block >= self.language_settings.min_block_check:
            adjusted_hours = (hours % 12) + 1
            if adjusted_hours == 13:
                adjusted_hours = 1
        # -------------------------------------------------Activate words based on minute block
        if str(minute_block) in self.language_settings.minute_blocks:
            for word in self.language_settings.minute_blocks[str(minute_block)]:
                self.activate_word(word)                   # the minute and its modifiers
            self.activate_word(self.language_settings.hour_words[adjusted_hours - 1])  # the hour        
        self.strip.show()

    def setcolor_x_y(self, x, y, color):                   #for rainbow effect
        if self.grid == "16":
            adjusted_x = x + 2                             # Skip the first two columns
            adjusted_y = y + 3                             # and first three rows
            if adjusted_x % 2 == 0:                        # Even columns: top to bottom
                led_index = (adjusted_x * 16) + adjusted_y
            else:                                          # Odd columns: bottom to top
                led_index = (adjusted_x * 16) + (15 - adjusted_y)
        else:                                              # For 11x10 grid
            if x % 2 == 0:                                 # Even columns: top to bottom
                led_index = 2 + (x * 10) + y
            else:                                          # Odd columns: bottom to top
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
        
        # Log what was merged (optional, helpful for debugging)
        overridden_keys = set(config_loc.keys()) & set(config_gen.keys())
        if overridden_keys:
            logging.info(f"User settings overriding system defaults for: {overridden_keys}")
        
        return merged_config
        
    except FileNotFoundError as e:
        logging.error(f"Required config file not found: {e}")
        logging.error(f"Please ensure {system_config_path} exists")
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

# Flask routes
@app.route("/")
def index():
    """Render the web interface with dynamic effect list."""
    initial_color = word_clock.letter_active_color
    initial_language = word_clock.language_settings.language
    initial_clock_type = word_clock.current_effect_id  # Now using effect ID
    initial_purist = word_clock.purist
    woordklok_name = word_clock.woordklok
    woordklok_version = word_clock.version
    woordklok_calibrate = word_clock.calibrate
    
    # Pass available effects to template
    available_effects = word_clock.available_effects
    
    return render_template(
        "index.html",
        initial_color=initial_color,
        initial_language=initial_language,
        initial_clock_type=initial_clock_type,
        initial_purist=initial_purist,
        woordklok_name=woordklok_name,
        woordklok_version=woordklok_version,
        woordklok_calibrate=woordklok_calibrate,
        available_effects=available_effects  # Pass effects list
    )

@app.route("/set_effect", methods=["POST"])
def set_effect():
    """Switch to a different effect"""
    try:
        data = request.get_json()
        effect_id = data.get("effect_id")
        
        if word_clock.set_effect(effect_id):
            return jsonify({
                "status": "success",
                "effect_name": word_clock.current_effect.name
            }), 200
        else:
            return jsonify({"error": "Effect not found"}), 404
            
    except Exception as e:
        logging.error(f"Failed to set effect: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_effect_settings", methods=["GET"])
def get_effect_settings():
    """Get HTML for current effect's settings"""
    try:
        if word_clock.current_effect:
            settings_html = word_clock.current_effect.get_settings_template()
            return jsonify({
                "settings_html": settings_html,
                "effect_name": word_clock.current_effect.name
            }), 200
        return jsonify({"settings_html": ""}), 200
    except Exception as e:
        logging.error(f"Failed to get effect settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/set_color", methods=["POST"])
def set_color():
    """Set the color of the letters."""
    try:
        red = int(request.form.get("red"))
        green = int(request.form.get("green"))
        blue = int(request.form.get("blue"))

        word_clock.letter_active_color = (red, green, blue)
        word_clock.dot_active_color = (red, green, blue)

        return "Color updated successfully!", 200
    except Exception as e:
        logging.error(f"Failed to set color: {e}")
        return "Failed to update color.", 500

@app.route('/update_settings', methods=['POST'])
def update_settings():
    try:
        data = request.get_json()
        
        # Update language if changed
        if 'language' in data:
            word_clock.update_language(data['language'])
        
        # Update purist mode if changed
        if 'purist' in data:
            word_clock.purist = data['purist'] == "true"
            logging.info(f"Purist mode set to: {word_clock.purist}")
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Failed to update settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_brightness", methods=["GET"])
def get_brightness():
    """Get the current brightness value."""
    try:
        if word_clock.light_sensor_type == "none":
            return jsonify({"brightness": f"No sensor: {word_clock.strip.getBrightness()}"}), 200
            
        if word_clock.light_sensor_type == "BH1750":
            lux = round(word_clock.light_sensor.measure_high_res(), 2)
        else:
            light_data = word_clock.light_sensor.get_current()
            lux = round(abs(light_data['lux']), 2)
        
        # Safely find brightness
        if word_clock.lut_in and word_clock.lut_out:
            index = min(bisect.bisect_right(word_clock.lut_in, lux), len(word_clock.lut_out) - 1)
            brt = word_clock.lut_out[index]
            brightness_display = f"{lux}: {brt}"
        else:
            brightness_display = f"{lux}: {word_clock.strip.getBrightness()}"
            
        return jsonify({"brightness": brightness_display}), 200
    except Exception as e:
        logging.error(f"Failed to fetch brightness: {e}")
        return jsonify({"brightness": "Error reading sensor"}), 200  # Return 200 with error message instead of 500

#--------------------------------------------------------calibration
@app.route("/calibration.html")
def calibration_page():
    """Serve the calibration interface"""
    return render_template("calibration.html")

@app.route("/set_mode", methods=["POST"])
def set_mode():
    try:
        data = request.get_json()
        mode = data.get("mode")
        if mode in ["normal", "calibration"]:
            word_clock.set_mode(mode)
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "Invalid mode"}), 400
    except Exception as e:
        logging.error(f"Mode switch failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_calibration_data", methods=["GET"])
def get_calibration_data():
    return jsonify({
        "lut_in": word_clock.lut_in,
        "lut_out": word_clock.lut_out
    })

@app.route("/calibration/get_current_brightness", methods=["GET"])
def get_current_brightness():
    """Get the current brightness value"""
    try:
        return jsonify({
            "brightness": word_clock.strip.getBrightness()
        }), 200
    except Exception as e:
        logging.error(f"Failed to get current brightness: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/calibration/current_light", methods=["GET"])
def get_current_light():
    """Get current light level"""
    try:
        if word_clock.light_sensor_type == "BH1750":
            lux = word_clock.light_sensor.measure_high_res()
        else:
            light_data = word_clock.light_sensor.get_current()
            lux = abs(light_data['lux'])
        return jsonify({"lux": lux}), 200
    except Exception as e:
        logging.error(f"Failed to read light level: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/calibration/set_temporary_brightness", methods=["POST"])
def set_temporary_brightness():
    """Set temporary brightness during calibration"""
    try:
        data = request.get_json()
        brightness = int(data.get("brightness"))
        
        if not 0 <= brightness <= 255:
            return jsonify({"error": "Brightness must be 0-255"}), 400
            
        word_clock.strip.setBrightness(brightness)
        word_clock.strip.show()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Failed to set temporary brightness: {e}")
        return jsonify({"error": str(e)}), 500

        return jsonify({"error": str(e)}), 500

@app.route("/calibration/save", methods=["POST"])
def save_calibration():
    """Save calibration to config"""
    try:
        data = request.get_json()
        word_clock.lut_in = data.get("lut_in", [])
        word_clock.lut_out = data.get("lut_out", [])
        
        # Save to config file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_path, 'r+') as f:
            config = json.load(f)
            config['LUT_IN'][word_clock.woordklok] = word_clock.lut_in
            config['LUT_OUT'][word_clock.woordklok] = word_clock.lut_out
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Failed to save calibration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/calibration/cancel", methods=["POST"])
def cancel_calibration():
    """Cancel calibration and restore original settings"""
    try:
        if hasattr(word_clock, 'calibration_data'):
            word_clock.strip.setBrightness(word_clock.calibration_data['original_brightness'])
            word_clock.strip.show()
            del word_clock.calibration_data
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Failed to cancel calibration: {e}")
        return jsonify({"error": str(e)}), 500
#------------------------------------------------------------calibration

# Main function to run the word clock
def run_clock():
    try:
        last_brightness_update = time.time()
        last_minute_check = time.time()
        
        while True:
            current_time = time.time()
            
            # Periodic updates
            if current_time - last_brightness_update >= word_clock.light_interval:
                word_clock.update_brightness()
                last_brightness_update = current_time
            
            if current_time - last_minute_check >= 60:
                if word_clock.current_effect and word_clock.current_effect.requires_time_update:
                    word_clock.current_effect.on_time_change()
                last_minute_check = current_time
            
            # Just update current effect - no fallback needed since we always have an effect
            if word_clock.current_effect:
                word_clock.current_effect.update()
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        # Cleanup
        if word_clock.current_effect:
            word_clock.current_effect.stop()
        word_clock.cls()
        word_clock.strip.show()

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=80, debug=False, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run the word clock
    run_clock()
