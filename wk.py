# -*- coding: utf-8 -*-
__version__ = "7.64"
# Woordklok - Buienradar logging off
import argparse
import json
import logging
import time
import datetime
import os
import threading
import random
import bisect
import math
from rpi_ws281x import PixelStrip, Color
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.serving import WSGIRequestHandler
from buienradar.buienradar import get_data, parse_data

# Light sensor client (reads from lux_daemon over Unix socket)
from lux_client import get_lux

# Import effect system
from effects import discover_effects

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("buienradar").setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__, template_folder='templates_plugin')


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
        self.woordklok = config["WOORDKLOK"]
        self.grid = config["GRID"]
        self.effect_full_panel = config["EFFECT_FULL_PANEL"]
        self.light_interval = config["LIGHT_INTERVAL"]
        self.language_settings = LanguageSettings(config, config["LANGUAGE"], self.grid)
        self.led_pin = config.get("LED_PIN", 18)       # use 18 if config is old and not yet has led pin
        self.led_freq_hz = 800000
        self.led_dma = 10
        self.led_channel = 0
        self.def_brightness = config["DEF_BRIGHTNESS"]
        self.background_brightness_factor = config["BG_BRIGHTNESS_FACTOR"]
        self.last_brightness = float(config["DEF_BRIGHTNESS"])
        self.background_color = config["BACKGROUND_COLOR"]
        self.letter_active_color = config["LETTER_ACTIVE_COLOR"]
        self.dot_active_color = config["DOT_ACTIVE_COLOR"]
        self.dot_inactive_color = config["DOT_INACTIVE_COLOR"]
        self.minute_dots = config["MINUTE_DOTS"].get(str(self.grid), {})
        self.dot_order = ["MLT", "MLB", "MRB", "MRT"]
        self.current_dot_index = 0
        self.dot_dark_color = config["DOT_DARK_COLOR"]
        self.default_effect = config["DEFAULT_EFFECT"]
        self.rand_color = config["RAND_COLOR"]
        self.light_sensor_type = config.get("SENSOR", "none")

        # Lux state — updated each frame by run_clock()
        # -1.0 means no sensor/daemon available
        self.lux = -1.0

        # EMA smoothing for brightness control
        # 0.20 = fast response, 0.90 = very slow/smooth
        self.smoothing_alpha = 0.20
        self._smoothed_lux   = -1.0       # internal EMA state

        self.sensor_scale = config["SENSOR_SCALE"]
        lut = config["LUT"]
        self.lut_in  = [row[0] for row in lut]
        self.lut_out = [row[1] for row in lut]

        self.temperature = 28
        self.precipitation = 5
        self.wind_speed = 5
        self.wind_direction = 270

        # Panel dimensions
        if self.grid == "16":
            self.panel_columns = 16
            self.panel_rows = 16
            self.led_count = 256
        else:
            self.panel_columns = 11
            self.panel_rows = 10
            self.led_count = 114

        self.clock_columns = 11
        self.clock_rows = 10
        self.columns = self.clock_columns
        self.rows = self.clock_rows

        logging.info(f"Woordklok    : {self.woordklok}")
        logging.info(f"version      : {self.version}")
        logging.info(f"Design       : Woosh")
        logging.info(f"Assist       : DeepSeek&Claude")
        logging.info(f"Made by      : GraWoosh Labs")
        logging.info(f"Random       : {self.rand_color}")
        logging.info(f"Language     : {self.language_settings.language}")
        logging.info(f"Grid         : {self.grid}")
        logging.info(f"LED_PIN      : {self.led_pin}")
        logging.info(f"Fullpanel    : {self.effect_full_panel}")
        logging.info(f"Light sensor : {self.light_sensor_type}")
        logging.info(f"Smoothing α  : {self.smoothing_alpha}")
        logging.info(f"Lut In       : {self.lut_in}")
        logging.info(f"Lut Out      : {self.lut_out}")

        # Initialize LED strip
        self.initialize_led()

        # Log lux daemon status
        initial_lux = get_lux()
        if initial_lux >= 0:
            logging.info(f"Lux daemon reachable – initial lux: {initial_lux:.2f}")
        else:
            logging.warning("Lux daemon not reachable – brightness control disabled")

        # Start weather thread
        self.weather_enabled = config["WEATHER_ENABLED"]
        if self.weather_enabled:
            self.weather_lat = float(config["WEATHER_LAT"])
            self.weather_lon = float(config["WEATHER_LON"])
            self.weather_update_interval = config.get("WEATHER_UPDATE_INTERVAL", 900)
            self._weather_thread = threading.Thread(target=self._weather_loop, daemon=True)
            self._weather_thread.start()
            logging.info("Weather background thread started")
        else:
            logging.info("Weather updates disabled")

        # Init effects
        self.effects = {}
        self.current_effect_id = self.default_effect

        effects_info = discover_effects()
        for effect_id, info in effects_info.items():
            try:
                effect_class = info['class']
                variant_id = info.get('variant_id')
                self.effects[effect_id] = effect_class(self, variant_id=variant_id)
            except Exception as e:
                logging.error(f"Failed to load effect {effect_id}: {e}")

        if "DEFAULT_EFFECT" in config:
            self.current_effect_id = config["DEFAULT_EFFECT"]
        elif self.current_effect_id in self.effects:
            pass
        else:
            self.current_effect_id = next(iter(self.effects.keys()), "normal")
        logging.info(f"Effect       : {self.current_effect_id}")

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

    def _weather_loop(self):
        for attempt in range(3):
            try:
                self._fetch_weather()
                logging.info("Initial weather data fetched")
                break
            except Exception as e:
                logging.warning(f"Initial weather fetch attempt {attempt+1} failed: {e}")
                time.sleep(5)
        else:
            logging.error("All initial weather fetch attempts failed – will retry later")

        while True:
            time.sleep(self.weather_update_interval)
            self._fetch_weather()

    def _fetch_weather(self):
        try:
            from buienradar.buienradar import get_data, parse_data

            result = get_data(latitude=self.weather_lat, longitude=self.weather_lon)
            if result is None or 'content' not in result:
                logging.warning("Weather fetch returned no data")
                return

            data = parse_data(result['content'], result.get('raincontent'),
                              self.weather_lat, self.weather_lon)
            if data is None or 'data' not in data:
                logging.warning("Weather parse returned no data")
                return

            current = data['data']
            self.temperature    = current.get('temperature',   self.temperature)
            self.wind_speed     = current.get('windspeed',     self.wind_speed)
            self.wind_direction = current.get('windazimuth',   self.wind_direction)
            self.precipitation  = current.get('precipitation', self.precipitation)

            logging.debug(f"Weather updated: T={self.temperature}°C, "
                          f"wind={self.wind_speed}m/s {self.wind_direction}°")
        except Exception as e:
            logging.error(f"Weather update failed: {e}")

    def update_brightness(self, raw_lux: float):
        """Apply EMA smoothing, sensor_scale and LUT to raw_lux, then set strip brightness.

        raw_lux is passed in from run_clock() so this method never calls get_lux() itself.
        """
        try:
            # EMA smoothing on the raw lux value
#            if self._smoothed_lux < 0:
#                self._smoothed_lux = raw_lux   # seed on first valid reading
#            else:
#                self._smoothed_lux = (self.smoothing_alpha * raw_lux
#                                      + (1 - self.smoothing_alpha) * self._smoothed_lux)
#            lux = self._smoothed_lux * self.sensor_scale

            lux = raw_lux * self.sensor_scale
            lux = max(self.lut_in[0], min(lux, self.lut_in[-1]))

            idx = bisect.bisect_right(self.lut_in, lux) - 1
            idx = max(0, min(idx, len(self.lut_in) - 2))

            x0, x1 = self.lut_in[idx],  self.lut_in[idx + 1]
            y0, y1 = self.lut_out[idx], self.lut_out[idx + 1]
            target = y0 if x1 == x0 else y0 + (y1 - y0) * (lux - x0) / (x1 - x0)

            self.last_brightness = target
            self.strip.setBrightness(int(self.last_brightness))

        except Exception as e:
            logging.error(f"Failed to update brightness: {e}")

    def set_background_brightness(self, value):
        self.background_brightness_factor = max(0.0, min(1.0, float(value)))

    def update_language(self, new_language):
        return self.language_settings.update_language(new_language)

    def set_effect(self, effect_id):
        if effect_id in self.effects:
            self.current_effect_id = effect_id
            self.cls()
            self.strip.show()
            current_effect = self.effects.get(effect_id)
            if current_effect:
                current_effect.draw()
            logging.info(f"Switched to effect: {effect_id}")
            return True
        return False

    def next_minuteled(self):
        prev_dot = self.dot_order[(self.current_dot_index - 1) % 4]
        self.set_led_color(self.minute_dots[prev_dot], (0, 0, 0))
        current_dot = self.dot_order[self.current_dot_index]
        self.set_led_color(self.minute_dots[current_dot], self.dot_dark_color)
        self.current_dot_index = (self.current_dot_index + 1) % 4

    def set_led_color(self, led_index, color):
        if 0 <= led_index < self.led_count:
            self.strip.setPixelColor(led_index, Color(color[0], color[1], color[2]))

    def map_grid_to_led(self, grid_index):
        if self.grid == "16":
            grd = grid_index + 34 + 5 * (grid_index // 11)
            col = grd % 16
            row = grd // 16
            if col % 2 == 0:
                led_index = (col * 16) + (15 - 1 - row)
            else:
                led_index = (col * 16) + row + 1
            return led_index
        else:
            col = grid_index % self.columns
            row = grid_index // self.columns
            if col % 2 == 0:
                led_index = 2 + (col * self.rows) + row
            else:
                led_index = 2 + (col * self.rows) + (self.rows - 1 - row)
            return led_index

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

        minute_dots = minutes % 5
        for dot, index in self.minute_dots.items():
            self.set_led_color(index, self.dot_active_color
                  if minute_dots >= list(self.minute_dots.keys()).index(dot) + 1
                  else self.dot_inactive_color)

        minute_block   = minutes // 5
        adjusted_hours = hours

        if not self.purist:
            for word in self.language_settings.it_is:
                self.activate_word(word)

        if minute_block >= self.language_settings.min_block_check:
            adjusted_hours = (hours % 12) + 1
            if adjusted_hours == 13:
                adjusted_hours = 1

        if str(minute_block) in self.language_settings.minute_blocks:
            for word in self.language_settings.minute_blocks[str(minute_block)]:
                self.activate_word(word)
            self.activate_word(self.language_settings.hour_words[adjusted_hours - 1])

        self.strip.show()

    def set_random_led(self, tint):
        if hasattr(self, 'effect_full_panel') and self.effect_full_panel:
            max_x = 15
            max_y = 15
        else:
            max_x = self.columns - 1
            max_y = self.rows - 1
        self.setcolor_x_y(
            random.randint(0, max_x),
            random.randint(0, max_y),
            self.random_color(tint)
        )

    def cls(self):
        if not self.effect_full_panel:
            for x in range(self.clock_columns):
                for y in range(self.clock_rows):
                    self.setcolor_x_y(x, y, self.background_color)
        else:
            for i in range(self.led_count):
                self.set_led_color(i, self.background_color)

    def setcolor_x_y(self, x, y, color):
        if self.grid == "16":
            if not self.effect_full_panel:
                panel_x = x + 2
                panel_y = y + 3
            else:
                panel_x = x
                panel_y = y
            if panel_x < 0 or panel_x >= 16 or panel_y < 0 or panel_y >= 16:
                return
            if panel_x % 2 == 0:
                led_index = (panel_x * 16) + (15 - panel_y)
            else:
                led_index = (panel_x * 16) + panel_y
        else:
            if x < 0 or x >= self.columns or y < 0 or y >= self.rows:
                return
            if x % 2 == 0:
                led_index = 2 + (x * 10) + y
            else:
                led_index = 2 + (x * 10) + (9 - y)
        self.set_led_color(led_index, color)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_merged_config():
    script_dir      = '/home/pi/ds'
    user_config_dir = '/home/pi/.wordclock'

    system_config_path = os.path.join(script_dir, 'config_gen.json')
    user_config_path   = os.path.join(user_config_dir, 'config_loc.json')

    try:
        with open(system_config_path) as f:
            config_gen = json.load(f)
        logging.info(f"Loaded system config from {system_config_path}")

        if os.path.exists(user_config_path):
            with open(user_config_path) as f:
                config_loc = json.load(f)
            logging.info(f"Loaded user config from {user_config_path}")
        else:
            config_loc = {}
            logging.warning(f"No user config found at {user_config_path}, using defaults only")

        return {**config_gen, **config_loc}

    except FileNotFoundError as e:
        logging.error(f"Required config file not found: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading config: {e}")
        return None


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

config     = load_merged_config()
word_clock = WordClock(config)

import web_routes
web_routes.init_routes(word_clock, app)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_clock():
    frame_delay = 0.01
    try:
        while True:
            # Call get_lux() once per frame — store result for both
            # update_brightness() and the web interface
            lux = get_lux()
            word_clock.lux = lux        # web_routes reads this; -1.0 = no sensor

            if lux >= 0:
                word_clock.update_brightness(lux)

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
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    flask_thread.daemon = True
    flask_thread.start()
    run_clock()
