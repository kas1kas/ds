# -*- coding: utf-8 -*-
__version__ = "8.13"
# Woordklok — single HARDWARE key drives all wiring and grid decisions
# reset_dots added
import json
import tomllib
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
# config_loc.toml sets:  hardware = "11x10V" | "11x10H" | "16x16V"
#
# Everything else (wiring name, LED count) is derived here.
# ---------------------------------------------------------------------------
_HARDWARE_PROFILES = {
    "11x10V": {"wiring": "vertical",   "led_count": 114},
    "11x10H": {"wiring": "horizontal", "led_count": 114},
    "16x16V": {"wiring": "matrix16",   "led_count": 256},
    "16x16":  {"wiring": "matrix16",   "led_count": 256},  # legacy alias
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
        # Resolve hardware profile from HARDWARE key.
        # ----------------------------------------------------------------
        hardware = config.get("HARDWARE", _HARDWARE_DEFAULT)

        if hardware not in _HARDWARE_PROFILES:
            logging.warning(
                f"Unknown HARDWARE '{hardware}', falling back to '{_HARDWARE_DEFAULT}'. "
                f"Valid values: {[k for k in _HARDWARE_PROFILES if k != '16x16']}"
            )
            hardware = _HARDWARE_DEFAULT

        if hardware == "16x16":
            logging.warning(
                "HARDWARE='16x16' is a legacy key — please update config_loc.toml "
                "to HARDWARE='16x16V'. Continuing with 16x16V settings."
            )
            hardware = "16x16V"

        profile        = _HARDWARE_PROFILES[hardware]
        self.hardware  = hardware
        wiring_name    = profile["wiring"]
        self.led_count = profile["led_count"]
        self.wiring    = Wiring(wiring_name)

        # Word grid is always 11×10
        self.clock_columns = 11
        self.clock_rows    = 10
        self.columns       = self.clock_columns
        self.rows          = self.clock_rows

        # Physical panel dimensions (used by effects)
        self.panel_columns, self.panel_rows = self.wiring.panel_dims

        # Minute dots: 1-based physical indices from config_loc.toml.
        # Dot order MD1→MD4 matches functional spec (MD1 lights first).
        # The user controls order by arranging MD1..MD4 in config_loc.toml.
        self.dot_order         = ["MD1", "MD2", "MD3", "MD4"]
        self.current_dot_index = 0
        minute_dots_all        = config.get("MINUTE_DOTS", {})
        self.minute_dots       = minute_dots_all.get(hardware, {})
        if not self.minute_dots:
            logging.warning(
                f"No MINUTE_DOTS entry for hardware '{hardware}' in config — dots disabled."
            )

        self.effect_full_panel            = config["EFFECT_FULL_PANEL"]
        self.light_interval               = config["LIGHT_INTERVAL"]
        self.language_settings            = LanguageSettings(config, config["LANGUAGE"])
        self.led_pin                      = config.get("LED_PIN", 18)
        self.led_freq_hz                  = 800000
        self.led_dma                      = 10
        self.led_channel                  = 0
        self.def_brightness               = config["DEF_BRIGHTNESS"]
        self.background_brightness_factor = config["BG_BRIGHTNESS_FACTOR"]
        self.last_brightness              = float(config["DEF_BRIGHTNESS"])
        self.background_color             = config["BACKGROUND_COLOR"]
        self.letter_active_color          = config["LETTER_ACTIVE_COLOR"]
        self.dot_active_color             = config["DOT_ACTIVE_COLOR"]
        self.dot_inactive_color           = config["DOT_INACTIVE_COLOR"]
        self.dot_dark_color               = config["DOT_DARK_COLOR"]
        self.default_effect               = config["DEFAULT_EFFECT"]
        self.rand_color                   = config["RAND_COLOR"]
        self.light_sensor_type            = config.get("SENSOR", "none")
        self.weather_enabled              = config["WEATHER_ENABLED"]
        self.weather_location             = config.get("WEATHER_LOCATION", "none")
        self.weather_lat                  = float(config.get("WEATHER_LAT", 5))
        self.weather_lon                  = float(config.get("WEATHER_LON", 5))
        self.weather_update_interval      = config.get("WEATHER_UPDATE_INTERVAL", 900)

        self.lux             = -1.0
        self.smoothing_alpha = 0.20
        self._smoothed_lux   = -1.0

        self.sensor_scale = config["SENSOR_SCALE"]
        lut = config["LUT"]
        if len(lut) < 2:
            logging.error("LUT must have at least 2 entries — check config_loc.toml")
            exit(1)
        self.lut_in  = [row[0] for row in lut]
        self.lut_out = [row[1] for row in lut]

        self.temperature    = 28
        self.precipitation  = 5
        self.wind_speed     = 5
        self.wind_direction = 270

        logging.info(f"Woordklok    : {self.woordklok}")
        logging.info(f"Version      : {self.version}")
        logging.info(f"Design       : Woosh")
        logging.info(f"Assist       : DeepSeek&Claude")
        logging.info(f"Made by      : GraWoosh Labs")
        logging.info(f"Hardware     : {self.hardware}  (wiring={wiring_name})")
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

        self.initialize_led()

        initial_lux = get_lux()
        if initial_lux >= 0:
            logging.info(f"Lux daemon   : reachable, initial lux={initial_lux:.2f}")
        else:
            logging.warning("Lux daemon   : not reachable — brightness control disabled")

        if self.weather_enabled:
            self._weather_thread = threading.Thread(target=self._weather_loop, daemon=True)
            self._weather_thread.start()
            logging.info(f"Weather      : enabled")
            logging.info(f"Location     : {self.weather_location}")
            logging.info(f"lat, lon     : {self.weather_lat}, {self.weather_lon}")
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
            self.clear_all()
            self.reset_dots()
            self.strip.show()
            current_effect = self.effects.get(effect_id)
            if current_effect:
                current_effect.draw()
            logging.info(f"Switched to effect: {effect_id}")
            return True
        return False

    def next_minuteled(self):
        """
        Advance the minute-dot animation by one step.
        Turns off the previous dot, lights the current dot in dot_dark_color,
        then advances the index. Called by EffectDark each tick.
        The dot order (MD1→MD4) is set by the user in config_loc.toml.
        """
        if not self.minute_dots:
            return
        prev_key    = self.dot_order[(self.current_dot_index - 1) % 4]
        current_key = self.dot_order[self.current_dot_index]
        # minute_dots values are 1-based from config; convert to 0-based for strip
        prev_led    = self.minute_dots.get(prev_key, -1) - 1
        current_led = self.minute_dots.get(current_key, -1) - 1
        if prev_led >= 0:
            self.set_led_color(prev_led, (0, 0, 0))
        if current_led >= 0:
            self.set_led_color(current_led, self.dot_dark_color)
        self.current_dot_index = (self.current_dot_index + 1) % 4

    def reset_dots(self):
        """
        Blank all four minute dot LEDs and reset the cycling index to 0.
        Called by set_effect() so that switching to dark mode always starts
        from a clean state, regardless of which dots were lit before.
        """
        self.current_dot_index = 0
        for dot_key in self.dot_order:
            led = self.minute_dots.get(dot_key, -1) - 1
            if led >= 0:
                self.set_led_color(led, (0, 0, 0))

    def set_led_color(self, led_index, color):
        """Set a single LED by 0-based physical index."""
        if 0 <= led_index < self.led_count:
            self.strip.setPixelColor(led_index, Color(color[0], color[1], color[2]))

    def map_grid_to_led(self, word_index_1based):
        """
        Convert a 1-based word-index (from config_gen.toml WORDS) to a
        0-based physical LED index via wiring.word_xy().

        word_index_1based: 1..110, left-to-right top-to-bottom (front view).
        Converts to 0-based (x, y) where y=0=top, then calls wiring.word_xy().
        """
        idx = word_index_1based - 1          # → 0-based flat index
        x   = idx % self.columns             # 0-based column, 0=left
        y   = idx // self.columns            # 0-based row,    0=top
        return self.wiring.word_xy(x, y)

    def activate_word(self, word):
        """Light all LEDs for a named word using 1-based config indices."""
        if word in self.language_settings.words:
            start, end = self.language_settings.words[word]
            for i in range(start, end + 1):
                led_index = self.map_grid_to_led(i)
                self.set_led_color(led_index, self.letter_active_color)

    def refresh_dots(self):
        """
        Paint active minute dot LEDs and call strip.show().
        Called every frame from run_clock() after effect.draw().

        On 11x10 hardware the dot LEDs are outside the panel area so the
        effect never touches them. Both active and inactive dots are written
        explicitly (inactive = dot_inactive_color).

        On 16x16V the dot LEDs are inside the full panel area. The effect's
        clear_screen() blanks them every frame, so inactive dots are already
        black — writing dot_inactive_color would paint a black square over
        whatever the effect drew there. Only active dots are written.
        """
        if not self.minute_dots:
            return
        minutes          = time.localtime().tm_min
        minute_remainder = minutes % 5
        dots_inside_panel = self.effect_full_panel and                             self.wiring.panel_dims != (self.clock_columns, self.clock_rows)
        for i, dot_key in enumerate(self.dot_order):
            led = self.minute_dots.get(dot_key, -1) - 1
            if led < 0:
                continue
            active = minute_remainder >= i + 1
            if active:
                self.set_led_color(led, self.dot_active_color)
            elif not dots_inside_panel:
                # Dot is outside the panel area — effect never blanks it,
                # so we must do it explicitly.
                self.set_led_color(led, self.dot_inactive_color)
            # else: dot is inside panel, effect already blanked it — leave it.
        self.strip.show()

    def update_clock(self):
        """
        Paint the word LEDs for the current time.
        Does NOT handle minute dots — those are managed exclusively by
        refresh_dots(), which is called every frame from run_clock().
        """
        now     = time.localtime()
        hours   = now.tm_hour % 12 or 12
        minutes = now.tm_min

        # --- Words ---
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

        # strip.show() is NOT called here — refresh_dots() in run_clock()
        # is the single flush point, ensuring dots are always written last.

    def set_random_led(self, tint):
        if self.effect_full_panel:
            self.set_led_color(random.randint(0, self.led_count - 1),
                               self.random_color(tint))
        else:
            self.setcolor_x_y(random.randint(0, self.columns - 1),
                               random.randint(0, self.rows - 1),
                               self.random_color(tint))

    def clear_all(self):
        """
        Wipe every LED on the strip to background_color.
        Used when switching effects to guarantee no residual pixels remain.
        Effects use setcolor_x_y() / clear_screen() in base_effect instead.
        """
        for i in range(self.led_count):
            self.set_led_color(i, self.background_color)

    def setcolor_x_y(self, x, y, color):
        """
        Set one LED by effect coordinate.

        Effect convention (matches all existing effects):
            x = 0 = RIGHT side of clock face (front view)
            x increases leftward
            y = 0 = TOP row, y increases downward

        wiring.py convention (matches spec, front-view):
            x = 0 = LEFT side
            x increases rightward

        The x-flip here bridges the two: wiring_x = (cols - 1 - x).
        This keeps all effects working unchanged while wiring.py
        remains correct per spec.

        effect_full_panel=True:  full panel (e.g. 16x16) via wiring.panel_xy()
        effect_full_panel=False: word grid area (11x10)   via wiring.word_xy()
        """
        if self.effect_full_panel:
            cols, rows = self.wiring.panel_dims
            if x < 0 or x >= cols or y < 0 or y >= rows:
                return
            self.set_led_color(self.wiring.panel_xy(cols - 1 - x, y), color)
        else:
            if x < 0 or x >= self.clock_columns or y < 0 or y >= self.clock_rows:
                return
            self.set_led_color(self.wiring.word_xy(self.clock_columns - 1 - x, y), color)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _toml_to_config(raw: dict) -> dict:
    """
    Flatten a parsed config_loc.toml dict into the canonical flat uppercase
    format that WordClock.__init__ expects.

    TOML uses lowercase keys and a [weather] sub-table.
    All top-level keys are uppercased; weather.* sub-keys are promoted
    to flat WEATHER_* keys to match the existing interface.
    """
    weather = raw.pop("weather", {})
    raw["WEATHER_ENABLED"]         = weather.get("enabled",         False)
    raw["WEATHER_LOCATION"]        = weather.get("location",        "none")
    raw["WEATHER_LAT"]             = weather.get("lat",             5.0)
    raw["WEATHER_LON"]             = weather.get("lon",             5.0)
    raw["WEATHER_UPDATE_INTERVAL"] = weather.get("update_interval", 900)
    return {k.upper(): v for k, v in raw.items()}


def load_merged_config():
    script_dir         = '/home/pi/ds'
    user_config_dir    = '/home/pi/.wordclock'
    system_config_path = os.path.join(script_dir, 'config_gen.toml')
    user_config_path   = os.path.join(user_config_dir, 'config_loc.toml')
    try:
        with open(system_config_path, "rb") as f:
            config_gen = tomllib.load(f)
        logging.info(f"Loaded system config from {system_config_path}")
        if os.path.exists(user_config_path):
            with open(user_config_path, "rb") as f:
                config_loc = _toml_to_config(tomllib.load(f))
            logging.info(f"Loaded user config from {user_config_path}")
        else:
            config_loc = {}
            logging.warning(f"No user config at {user_config_path}, using defaults")
        return {**config_gen, **config_loc}
    except FileNotFoundError as e:
        logging.error(f"Required config file not found: {e}")
        return None
    except tomllib.TOMLDecodeError as e:
        logging.error(f"Invalid TOML in config file: {e}")
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
            if now - last_lux_time >= word_clock.light_interval:
                lux = get_lux()
                word_clock.lux = lux
                last_lux_time  = now
                if lux >= 0:
                    word_clock.update_brightness(lux)

            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect:
                current_effect.draw()

            # Ensure minute dots always reflect the current time, even on
            # frames where the effect returned early without calling update_clock().
            word_clock.refresh_dots()

            time.sleep(frame_delay)
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        word_clock.clear_all()
        word_clock.strip.show()


if __name__ == "__main__":
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    flask_thread.daemon = True
    flask_thread.start()
    run_clock()
