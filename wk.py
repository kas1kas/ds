# woordklok v5.28
# hour_words via config Line 180
# for 11x10 and 16x16 grid
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
from flask import Flask, request, render_template, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
app = Flask(__name__)

# create the core routines as Class
class WordClock:
    def __init__(self, config):
        self.version = config["VERSION"]
        self.purist = config["PURIST"]
        self.woordklok = config["WOORDKLOK"]
        self.language = config["LANGUAGE"]
        self.grid = config["GRID"]
        self.light_interval = config["LIGHT_INTERVAL"]
        self.led_pin = config["LED_PIN"]
        self.led_freq_hz = config["LED_FREQ_HZ"]
        self.led_dma = config["LED_DMA"]
        self.led_channel = config["LED_CHANNEL"]
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
        self.lut_in =  config.get("LUT_IN").get(self.woordklok,{})
        self.lut_out=  config.get("LUT_OUT").get(self.woordklok,{}) 
        self.CURSOR_UP = "\x1b[2A"
        self.minute_blocks = config["MINUTE_BLOCKS"].get(self.language,{})
        self.words = config["WORDS"].get(self.language, {}).get(str(self.grid), {})
        self.min_block_check = config["MIN_BLOCK_CHECK"].get(self.language,{})
        self.hour_words = config["HOUR_WORDS"].get(self.language,{})

        if self.grid=="16":
          self.led_count = 256
          self.columns =16
          self.rows=16
        else:
          self.led_count = 114
          self.columns = 11
          self.rows = 10

        logging.info(f"Design   : Woosh") 
        logging.info(f"Made by  : GraWoosh Labs") 
        logging.info(f"Woordklok: {self.woordklok}")
        logging.info(f"Clock    : {self.clock_type}") 
        logging.info(f"Random   : {self.rand_color}") 
        logging.info(f"Language : {self.language}")
        logging.info(f"Grid     : {self.grid}") 
        logging.info(f"Sensor   : TSL2591") 
        logging.info(f"Lut In   : {self.lut_in}")
        logging.info(f"Lut Out  : {self.lut_out}")
        # Initialize LED strip
        try:
            self.strip = PixelStrip(
                self.led_count, self.led_pin, self.led_freq_hz,
                self.led_dma, False, 100, self.led_channel
            )
            self.strip.begin()
            logging.info("LED strip initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize LED strip: {e}")
            exit(1)

        # Initialize TSL2591 light sensor
        try:
            self.light_sensor = tsl2591()
            logging.info("TSL2591 light sensor initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize TSL2591 light sensor: {e}")
            exit(1)

    # subs ----------------------------------------------------------------------------------

    def set_random_led(self, tint):
       self.setcolor_x_y(random.randint(0,10),random.randint(0,9),self.random_color(tint))
       
    def random_color(self, tint):
      if tint == "blue":
         r = random.randint(  29, 69)   # shades of blue 
         g = random.randint(  31, 71)
         b = random.randint(105,245)
      elif tint == "orange":
         r = random.randint( 100,155)   # shades of orange 
         g = random.randint(  20, 40)
         b = random.randint(   0,  2)
      return (r, g, b) 
      
    def cls(self):
        for i in range(self.led_count):
           self.set_led_color(i, self.background_color)

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
      try:
          light_data = self.light_sensor.get_current()
          lux = abs(light_data['lux'])
      except Exception as e:
          logging.error(f"Failed to read light level: {e}")
          return
      index = bisect.bisect_right(self.lut_in, lux)
      brt = self.lut_out[index]
      self.strip.setBrightness(brt)

    def activate_word(self, word):
        if word in self.words:
            start, end = self.words[word]
            for i in range(start, end + 1):
                led_index = self.map_grid_to_led(i)
                if led_index != -1:
                    self.set_led_color(led_index, self.letter_active_color) 
                    
    def update_clock(self):
        """Update the clock display based on the current time."""
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
        # -------------------------------------------------Show "HET IS"
        if not self.purist:
            if self.language == "NL":
                self.activate_word("HET")
            elif self.language == "EN":
                self.activate_word("IT")
            self.activate_word("IS")    
        # -------------------------------------------------Adjust hour per language minutes
        if minute_block >= self.min_block_check:
            adjusted_hours = (hours % 12) + 1
            if adjusted_hours == 13:
                adjusted_hours = 1
        # -------------------------------------------------Activate words based on minute block
        if str(minute_block) in self.minute_blocks:
            for word in self.minute_blocks[str(minute_block)]:
                self.activate_word(word)
            self.activate_word(self.hour_words[adjusted_hours - 1])
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
    
    def kwheel(self, pos):
         if pos < 85:
            return (pos * 3, 255 - pos * 3, 0), Color(255-pos * 3, pos * 3, 255)
         elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3), Color(pos * 3, 255, 255-pos * 3)
         else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3), Color(255, 255-pos * 3, pos * 3)
    # End Subs ------------------------------------------------------------------------------

def load_config(config_file):
    """Load configuration from a JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_file)
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        print(f"Error: {config_file} not found at {config_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: {config_file} is not a valid JSON file.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Initialize word clock
config = load_config("config.json")
word_clock = WordClock(config)

# Flask routes
@app.route("/")
def index():
    """Render the web interface with the initial settings."""
    initial_color = word_clock.letter_active_color
    initial_language = word_clock.language
    initial_clock_type = word_clock.clock_type
    initial_purist = word_clock.purist
    woordklok_name = word_clock.woordklok + word_clock.version
    
    return render_template(
        "index.html",
        initial_color=initial_color,
        initial_language=initial_language,
        initial_clock_type=initial_clock_type,
        initial_purist=initial_purist,
        woordklok_name = word_clock.woordklok + word_clock.version
    )

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

@app.route("/set_language", methods=["POST"])
def set_language():
    """Set the language of the word clock."""
    try:
        language = request.form.get("language")
        if language in ["NL", "EN"]:
            word_clock.language = language
            word_clock.words = config["WORDS"].get(language, {}).get(word_clock.grid, {})
            word_clock.minute_blocks = config["MINUTE_BLOCKS"].get(language, {})
            word_clock.min_block_check = config["MIN_BLOCK_CHECK"].get(language, {})
            return "Language updated successfully!", 200
        else:
            return "Invalid language.", 400
    except Exception as e:
        logging.error(f"Failed to set language: {e}")
        return "Failed to update language.", 500

@app.route("/set_clock_type", methods=["POST"])
def set_clock_type():
    """Set the clock type."""
    try:
        clock_type = request.form.get("clock_type")
        if clock_type in ["regular", "random", "rainbow", "dark", "test"]:
            word_clock.clock_type = clock_type
            return "Clock type updated successfully!", 200
        else:
            return "Invalid clock type.", 400
    except Exception as e:
        logging.error(f"Failed to set clock type: {e}")
        return "Failed to update clock type.", 500

@app.route("/set_purist", methods=["POST"])
def set_purist():
    """Set the purist mode."""
    try:
        purist = request.form.get("purist")
        if purist in ["true", "false"]:
            word_clock.purist = purist == "true"
            return "Purist mode updated successfully!", 200
        else:
            return "Invalid purist mode.", 400
    except Exception as e:
        logging.error(f"Failed to set purist mode: {e}")
        return "Failed to update purist mode.", 500

@app.route("/get_brightness", methods=["GET"])
def get_brightness():
    """Get the current brightness value."""
    try:
        light_data = word_clock.light_sensor.get_current()
        lux = round(abs(light_data['lux']),2)
        index = bisect.bisect_right(word_clock.lut_in, lux)
        brt = word_clock.lut_out[index]
        brightness_display = f"{lux}: {brt}"
        return jsonify({"brightness": brightness_display}), 200
    except Exception as e:
        logging.error(f"Failed to fetch brightness: {e}")
        return jsonify({"error": "Failed to fetch brightness"}), 500

# Main function to run the word clock
def run_clock():

    def onlyx(interval):
        if not hasattr(onlyx, "last_time"):
        # Initialize the last_time attribute if it doesn't exist
            onlyx.last_time = time.time() - interval  # Ensure it runs the first time
        current_time = time.time()
        if current_time - onlyx.last_time >= interval:
            onlyx.last_time = current_time
            return True
        return False

    """Run the word clock in a separate thread."""
    try:
      last_time = time.time()
      while True:
        if onlyx(word_clock.light_interval):
           word_clock.update_brightness()

        if word_clock.clock_type == "regular":
           word_clock.cls()
           word_clock.update_clock()

        elif word_clock.clock_type == "test":
           word_clock.update_clock()

        elif word_clock.clock_type == "dark":
           if time.time() - last_time >= 5:  # Every second
              word_clock.cls()
               
              # Turn off previous LED
              prev_dot = word_clock.dot_order[(word_clock.current_dot_index - 1) % 4]
              word_clock.set_led_color(word_clock.minute_dots[prev_dot], (0, 0, 0))
              
              # Turn on current LED
              current_dot = word_clock.dot_order[word_clock.current_dot_index]
              word_clock.set_led_color(word_clock.minute_dots[current_dot], word_clock.dot_dark_color)
              
              # Advance to next LED
              word_clock.current_dot_index = (word_clock.current_dot_index + 1) % 4
              last_time = time.time()
           word_clock.strip.show()

        elif word_clock.clock_type == "random":
            word_clock.set_random_led(word_clock.rand_color)
            word_clock.update_clock()
            
        elif word_clock.clock_type == "rainbow":
           for j in range(256 * 5):
               for x in range(11):
                   for y in range(10):
                      k=(x * y + j) & 255
                      b,w = word_clock.kwheel(k)
                      word_clock.setcolor_x_y(x,y,b)
               word_clock.update_clock()
               time.sleep(0.01)
           word_clock.update_clock()
            
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        # Clean up on exit
        for i in range(word_clock.led_count):
            word_clock.set_led_color(i, word_clock.background_color)
        word_clock.strip.show()

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=80))
    flask_thread.daemon = True
    flask_thread.start()

    # Run the word clock
    run_clock()
