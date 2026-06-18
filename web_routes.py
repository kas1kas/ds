# -*- coding: utf-8 -*-
__version__ = "7.65"
import logging
import bisect
import time
import os
import json
import subprocess
from flask import request, jsonify, render_template

# These will be set by init_routes
word_clock = None
app        = None
_pi_model  = "Unknown"

def init_routes(clock, flask_app):
    """Initialize routes with the word clock instance"""
    global word_clock, app, _pi_model
    word_clock = clock
    app        = flask_app

    # Read Raspberry Pi model once at startup — the file is null-terminated.
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            _pi_model = f.read().rstrip('\x00').strip()
    except Exception as e:
        logging.warning(f"Could not read Pi model: {e}")
        _pi_model = "Unknown"

    register_routes()
    logging.info(f"Pi model     : {_pi_model}")
    logging.info("Web routes initialized")

def register_routes():
    """Register all Flask routes"""

    # ================== MAIN PAGE ==================

    @app.route("/")
    def index():
        """Render the web interface with dynamic effect list."""
        initial_color     = word_clock.letter_active_color
        initial_language  = word_clock.language_settings.language
        initial_effect    = word_clock.current_effect_id
        initial_purist    = word_clock.purist
        woordklok_name    = word_clock.woordklok
        woordklok_version = word_clock.version

        # Sensor is active when the daemon is reachable and returning a valid lux.
        # word_clock.lux is updated every frame by run_clock(); -1.0 means no sensor.
        has_light_sensor = word_clock.lux >= 0

        available_effects = []
        for effect_id, effect in word_clock.effects.items():
            available_effects.append({
                'id': effect_id,
                'name': getattr(effect, 'name', effect_id.capitalize())
            })

        logging.info(f"Rendering index: language={initial_language}, purist={initial_purist}")
        return render_template(
            "index.html",
            initial_color=initial_color,
            initial_language=initial_language,
            initial_clock_type=initial_effect,
            initial_purist=initial_purist,
            woordklok_name=woordklok_name,
            woordklok_location=word_clock.weather_location,
            woordklok_lat=word_clock.weather_lat,
            woordklok_lon=word_clock.weather_lon,
            woordklok_version=woordklok_version,
            pi_model=_pi_model,
            available_effects=available_effects,
            has_light_sensor=has_light_sensor,
            auto_dark_enabled=word_clock.auto_dark_enabled,
            auto_dark_threshold=word_clock.auto_dark_threshold,
        )

    # ================== EFFECT ROUTES ==================

    @app.route("/set_effect", methods=["POST"])
    def set_effect():
        """Switch to a different effect"""
        try:
            data = request.get_json()
            effect_id = data.get("effect_id")
            if word_clock.set_effect(effect_id):
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"error": "Effect not found"}), 404
        except Exception as e:
            logging.error(f"Failed to set effect: {e}")
            return jsonify({"error": str(e)}), 500

    # ================== COLOR ROUTES ==================

    @app.route("/set_color", methods=["POST"])
    def set_color():
        """Set the color of the letters."""
        try:
            red   = int(request.form.get("red"))
            green = int(request.form.get("green"))
            blue  = int(request.form.get("blue"))
            word_clock.letter_active_color = (red, green, blue)
            word_clock.dot_active_color    = (red, green, blue)
            return "Color updated successfully!", 200
        except Exception as e:
            logging.error(f"Failed to set color: {e}")
            return "Failed to update color.", 500

    # ================== SETTINGS ROUTES ==================

    @app.route('/update_settings', methods=['POST'])
    def update_settings():
        try:
            data = request.get_json()
            if 'language' in data:
                word_clock.update_language(data['language'])
            if 'purist' in data:
                word_clock.purist = data['purist'] == "true"
                logging.info(f"Purist mode set to: {word_clock.purist}")
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logging.error(f"Failed to update settings: {e}")
            return jsonify({"error": str(e)}), 500

    # ================== BRIGHTNESS ROUTES ==================

    @app.route("/show_brightness", methods=["GET"])
    def show_brightness():
        try:
            lux = word_clock.lux           # raw lux set each frame by run_clock()
            if lux < 0:
                return jsonify({"brightness": "No sensor"}), 200
            brightness = int(round(word_clock.last_brightness))
            return jsonify({"brightness": f"{round(lux, 1)}  ->  {brightness}"}), 200
        except Exception as e:
            logging.error(f"Failed to fetch brightness: {e}")
            return jsonify({"brightness": "Error reading sensor"}), 500

    # ================== BACKGROUND BRIGHTNESS ROUTES ==================

    @app.route('/set_background_brightness', methods=['POST'])
    def set_background_brightness():
        data  = request.json
        value = data.get('value', 1.0)
        if word_clock:
            word_clock.set_background_brightness(value)
            return jsonify({'success': True, 'value': value})
        return jsonify({'success': False}), 400

    @app.route('/get_background_brightness', methods=['GET'])
    def get_background_brightness():
        if word_clock:
            value = word_clock.background_brightness_factor
            return jsonify({'value': value})
        return jsonify({'value': 1.0})

    # ================== AUTO-DARK ROUTES ==================

    @app.route('/set_auto_dark', methods=['POST'])
    def set_auto_dark():
        """Enable/disable auto-dark and adjust its lux threshold."""
        try:
            data = request.get_json()
            if 'enabled' in data:
                word_clock.auto_dark_enabled = bool(data['enabled'])
                # If disabling while active, restore the saved effect immediately.
                if not word_clock.auto_dark_enabled and word_clock._auto_dark_active:
                    word_clock._auto_dark_active = False
                    restore = word_clock._pre_dark_effect or word_clock.default_effect
                    word_clock.set_effect(restore)
                    logging.info(f"Auto-dark disabled — restored effect '{restore}'")
            if 'threshold' in data:
                word_clock.auto_dark_threshold = float(data['threshold'])
            logging.info(
                f"Auto-dark updated: enabled={word_clock.auto_dark_enabled}, "
                f"threshold={word_clock.auto_dark_threshold}"
            )
            return jsonify({
                'success':   True,
                'enabled':   word_clock.auto_dark_enabled,
                'threshold': word_clock.auto_dark_threshold,
            }), 200
        except Exception as e:
            logging.error(f"Failed to update auto-dark: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/get_auto_dark', methods=['GET'])
    def get_auto_dark():
        """Return current auto-dark settings."""
        return jsonify({
            'enabled':   word_clock.auto_dark_enabled,
            'threshold': word_clock.auto_dark_threshold,
        }), 200
