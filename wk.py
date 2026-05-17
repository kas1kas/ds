# -*- coding: utf-8 -*-
__version__ = "7.78"
# Woordklok — single HARDWARE key drives all wiring and grid decisions
import json
import logging
import time
import os
import threading
import random
import bisect
from rpi_ws281x import PixelStrip, Color
from flask import Flask, request, render_template, jsonify, send_file
from buienradar.buienradar import get_data, parse_data

from lux_client import get_lux
from effects import discover_effects
from wiring import Wiring

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("buienradar").setLevel(logging.WARNING)

app = Flask(__name__, template_folder='templates_plugin')

# ---------------------------------------------------------------------------
# Hardware profiles — single source of truth
#
# config_loc.json sets one key:  "HARDWARE": "11x10V" | "11x10H" | "16x16"
#
# Everything else (wiring name, grid size, LED count) is derived here.
# Programmers add new hardware by adding an entry to this dict.
# Users never see the internal wiring/grid names.
# ---------------------------------------------------------------------------
_HARDWARE_PROFILES = {
    "11x10V": {"wiring": "vertical",   "grid": "11", "led_count": 114},
    "11x10H": {"wiring": "horizontal", "grid": "11", "led_count": 114},
    "16x16":  {"wiring": "matrix16",   "grid": "16", "led_count": 256},
}
_HARDWARE_DEFAULT = "11x10V"


class LanguageSettings:
    def __init__(self, config, language):
        self.config   = config
        self.language = language
        self.load_language_settings()

    def load_language_settings(self):
        self.it_is           = self.config["IT_IS"].get(self.language, {})
        self.minute_blocks   = self.config["MINUTE_BLOCKS"].get(self.language, {})
        self.words           = self.config["WORDS"].get(self.language, {})
        self.min_block_check = self.config["MIN_BLOCK_CHECK"].get(self.language, {})
        self.hour_words      = self.config["HOUR_WORDS"].get(self.language, {})

    def update_language(self, new_language):
        if new_language in ["NL", "EN"]:
            self.language = new_language
            self.load_language_settings()
            return True
        return False


class WordClock:
    def __init__(self, config):
        self.version   = __version__
        self.purist    = config["PURIST"]
        self.woordklok = config["WOORDKLOK"]

        # ----------------------------------------------------------------
        # Resolve hardware profile from single HARDWARE key.
        # Falls back gracefully if old GRID/WIRING keys are still present.
        # ----------------------------------------------------------------
        hardware = config.get("HARDWARE")
        if hardware is None:
            # Backward compatibility: derive from old GRID + WIRING keys
            old_grid   = config.get("GRID", "11")
            old_wiring = config.get("WIRING", "vertical")
            _legacy_map = {
                ("11", "vertical"):   "11x10V",
                ("11", "horizontal"): "11x10H",
                ("16", "matrix16"):   "16x16",
            }
            hardware = _legacy_map.get((old_grid, old_wiring), _HARDWARE_DEFAULT)
            logging.warning(
                f"HARDWARE key missing — derived '{hardware}' from "
                f"GRID='{old_grid}' + WIRING='{old_wiring}'. "
                f"Please update config_loc.json."
            )

        if hardware not in _HARDWARE_PROFILES:
            logging.warning(
                f"Unknown HARDWARE '{hardware}', falling back to '{_HARDWARE_DEFAULT}'. "
                f"Valid values: {list(_HARDWARE_PROFILES)}"
            )
            hardware = _HARDWARE_DEFAULT

        profile           = _HARDWARE_PROFILES[hardware]
        self.hardware     = hardware
        self.grid         = profile["grid"]       # "11" or "16" — used for word lookup
        wiring_name       = profile["wiring"]     # internal name, not exposed to user
        self.led_count    = profile["led_count"]
        self.wiring       = Wiring(wiring_name)

        # Word grid is always 11×10
        self.clock_columns = 11
        self.clock_rows    = 10
        self.columns       = self.clock_columns
        self.rows          = self.clock_rows

        # Physical panel dimensions (used by effects)
        self.panel_columns, self.panel_rows = self.wiring.panel_dims

        # Minute dots: physical indices from config, keyed by hardware name
        self.dot_order         = ["ML1", "ML2", "ML3", "ML4"]
        self.current_dot_index = 0
        self.minute_dots       = config.get("MINUTE_DOTS", {}).get(hardware, {})
        if not self.minute_dots:
            logging.warning(
                f"No MINUTE_DOTS entry for hardware '{hardware}' — dots disabled."
            )

        self.effect_full_panel           = config["EFFECT_FULL_PANEL"]
        self.light_interval              = config["LIGHT_INTERVAL"]
        self.language_settings           = LanguageSettings(config, config["LANGUAGE"])
        self.led_pin                     = config.get("LED_PIN", 18)
        self.led_freq_hz                 = 800000
        self.led_dma                     = 10
        self.led_channel                 = 0
        self.def_brightness              = config["DEF_BRIGHTNESS"]
        self.background_brightness_factor = config["BG_BRIGHTNESS_FACTOR"]
        self.last_brightness             = float(config["DEF_BRIGHTNESS"])
        self.background_color            = config["BACKGROUND_COLOR"]
        self.letter_active_color         = config["LETTER_ACTIVE_COLOR"]
        self.dot_active_color            = config["DOT_ACTIVE_COLOR"]
        self.dot_inactive_color          = config["DOT_INACTIVE_COLOR"]
        self.dot_dark_color              = config["DOT_DARK_COLOR"]
        self.default_effect              = config["DEFAULT_EFFECT"]
        self.rand_color                  = config["RAND_COLOR"]
        self.light_sensor_type           = config.get("SENSOR", "none")
        self.weather_enabled             = config["WEATHER_ENABLED"]
        self.weather_location            = config.get("WEATHER_LOCATION", "none")
        self.weather_lat                 = float(config.get("WEATHER_LAT", 5))
        self.weather_lon                 = float(config.get("WEATHER_LON", 5))
        self.weather_update_interval     = config.get("WEATHER_UPDATE_INTERVAL", 900)

        self.lux             = -1.0
        self.smoothing_alpha = 0.20
        self._smoothed_lux   = -1.0

        self.sensor_scale = config["SENSOR_SCALE"]
        lut = config["LUT"]
        self.lut_in  = [row[0] for row in lut]
        self.lut_out = [row[1] for row in lut]

        self.temperature    = 28
        self.precipitation  = 5
        self.wind_speed     = 5
        self.wind_direction = 270

        logging.info(f"Woordklok    : {self.woordklok}")
        logging.info(f"version      : {self.version}")
        logging.info(f"Design       : Woosh")
        logging.info(f"Assist       : DeepSeek&Claude")
        logging.info(f"Made by      : GraWoosh Labs")
        logging.info(f"Hardware     : {self.hardware}  (wiring={wiring_name} grid={self.grid})")
        logging.info(f"Panel        : {self.panel_columns}×{self.panel_rows}")
        logging.info(f"Minute dots  : {self.minute_dots}")
        logging.info(f"Random       : {self.rand_color}")
        logging.info(f"Language     : {self.language_settings.language}")
        logging.info(f"LED_PIN      : {self.led_pin}")
        logging.info(f"Fullpanel    : {self.effect_full_panel}")
        logging.info(f"Light sensor : {self.light_sensor_type}")
        logging.info(f"Smoothing α  : {self.smoothing_alpha}")
        logging.info(f"Lut In       : {self.lut_in}")
        logging.info(f"Lut Out      : {self.lut_out}")
        logging.info(f"Location     : {self.weather_location}")

        self.initialize_led()

        initial_lux = get_lux()
        if initial_lux >= 0:
            logging.info(f"Lux daemon   : reachable, initial lux={initial_lux:.2f}")
        else:
            logging.warning("Lux daemon   : not reachable — brightness control disabled")

        if self.weather_enabled:
            self._weather_thread = threading.Thread(target=self._weather_loop, daemon=True)
            self._weather_thread.start()
            logging.info(f"Weather      : enabled  lat={self.weather_lat} lon={self.weather_lon}")
        else:
            logging.info("Weather      : disabled")

        self.effects = {}
        self.current_effect_id = self.default_effect

        effects_info = discover_effects()
        for effect_id, info in effects_info.items():
            try:
                self.effects[effect_id] = info['class'](self, variant_id=info.get('variant_id'))
            except Exception as e:
                logging.error(f"Failed to load effect {effect_id}: {e}")

        if "DEFAULT_EFFECT" in config:
            self.current_effect_id = config["DEFAULT_EFFECT"]
        elif self.current_effect_id not in self.effects:
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
            logging.info("LED strip    : initialized")
        except Exception as e:
            logging.error(f"LED strip init failed: {e}")
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
            logging.error("All initial weather fetch attempts failed")
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
            logging.debug(f"Weather: T={self.temperature}°C wind={self.wind_speed}m/s {self.wind_direction}°")
        except Exception as e:
            logging.error(f"Weather update failed: {e}")

    def update_brightness(self, raw_lux: float):
        try:
            lux = raw_lux * self.sensor_scale
            lux = max(self.lut_in[0], min(lux, self.lut_in[-1]))
            idx = bisect.bisect_right(self.lut_in, lux) - 1
            idx = max(0, min(idx, len(self.lut_in) - 2))
            x0, x1 = self.lut_in[idx],  self.lut_in[idx + 1]
            y0, y1 = self.lut_out[idx], self.lut_out[idx + 1]
            target = y1 if x1 == x0 or lux >= x1 else y0 + (y1-y0)*(lux-x0)/(x1-x0)
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
        prev_dot    = self.dot_order[(self.current_dot_index - 1) % 4]
        current_dot = self.dot_order[self.current_dot_index]
        self.set_led_color(self.minute_dots[prev_dot], (0, 0, 0))
        self.set_led_color(self.minute_dots[current_dot], self.dot_dark_color)
        self.current_dot_index = (self.current_dot_index + 1) % 4

    def set_led_color(self, led_index, color):
        if 0 <= led_index < self.led_count:
            self.strip.setPixelColor(led_index, Color(color[0], color[1], color[2]))

    def map_grid_to_led(self, grid_index):
        """Flat config index → physical strip index via wiring.word_xy()."""
        return self.wiring.word_xy(grid_index % self.columns,
                                   grid_index // self.columns)

    def activate_word(self, word):
        if word in self.language_settings.words:
            start, end = self.language_settings.words[word]
            for i in range(start, end + 1):
                led_index = self.map_grid_to_led(i)
                if led_index != -1:
                    self.set_led_color(led_index, self.letter_active_color)

    def update_clock(self):
        now     = time.localtime()
        hours   = now.tm_hour % 12 or 12
        minutes = now.tm_min

        minute_dots = minutes % 5
        for i, dot in enumerate(self.dot_order):
            active = minute_dots >= i + 1
            self.set_led_color(self.minute_dots[dot],
                               self.dot_active_color if active else self.dot_inactive_color)

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
        if self.effect_full_panel:
            self.set_led_color(random.randint(0, self.led_count - 1),
                               self.random_color(tint))
        else:
            self.setcolor_x_y(random.randint(0, self.columns - 1),
                               random.randint(0, self.rows - 1),
                               self.random_color(tint))

    def cls(self):
        """Clear the word grid using word coordinates (y=0=bottom)."""
        for x in range(self.clock_columns):
            for y in range(self.clock_rows):
                self.set_led_color(self.wiring.word_xy(x, y), self.background_color)

    def setcolor_x_y(self, x, y, color):
        """
        Set one LED by panel coordinate: x=0..W-1 left-right, y=0..H-1 top-bottom.
        y=0 is always the TOP row for all hardware variants.

        effect_full_panel=True:  full panel dimensions (e.g. 16x16)
        effect_full_panel=False: word grid dimensions (11x10)

        Both cases use wiring.panel_xy() — no y-convention difference.
        map_grid_to_led() and cls() use wiring.word_xy() (y=0=bottom) separately.
        """
        if self.effect_full_panel:
            cols, rows = self.wiring.panel_dims
        else:
            cols, rows = self.clock_columns, self.clock_rows
        if x < 0 or x >= cols or y < 0 or y >= rows:
            return
        self.set_led_color(self.wiring.panel_xy(x, y), color)


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
            logging.warning(f"No user config at {user_config_path}, using defaults")
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
    frame_delay   = 0.01
    last_lux_time = 0.0          # force an immediate read on first frame
    try:
        while True:
            now = time.time()

            # Poll lux at light_interval cadence (default 1s), not every frame.
            # get_lux() opens a socket each call; the sensor only updates
            # every ~220 ms so polling at 100 fps is pure wasted overhead.
            if now - last_lux_time >= word_clock.light_interval:
                lux = get_lux()
                word_clock.lux = lux
                last_lux_time  = now
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
