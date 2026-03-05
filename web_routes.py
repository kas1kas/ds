__version__ = "7.14"
import logging
import bisect
import time
import os
import json
import subprocess
from flask import request, jsonify, render_template

# These will be set by init_routes
word_clock = None
app = None

def init_routes(clock, flask_app):
    """Initialize routes with the word clock instance"""
    global word_clock, app
    word_clock = clock
    app = flask_app
    
    # Register all routes
    register_routes()
    
    logging.info("Web routes initialized")

def register_routes():
    """Register all Flask routes"""
      
    # ================== MAIN PAGE ==================
    
    @app.route("/")
    def index():
        """Render the web interface with dynamic effect list."""
        initial_color = word_clock.letter_active_color
        initial_language = word_clock.language_settings.language
        initial_effect = word_clock.current_effect_id
        initial_purist = word_clock.purist
        woordklok_name = word_clock.woordklok
        woordklok_version = word_clock.version
        woordklok_calibrate = word_clock.calibrate
        has_light_sensor = word_clock.light_sensor_type != "none"

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
            woordklok_version=woordklok_version,
            woordklok_calibrate=woordklok_calibrate,
            available_effects=available_effects,
            has_light_sensor=has_light_sensor
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
            red = int(request.form.get("red"))
            green = int(request.form.get("green"))
            blue = int(request.form.get("blue"))
    
            word_clock.letter_active_color = (red, green, blue)
            word_clock.dot_active_color = (red, green, blue)
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
            
            if word_clock.lut_in and word_clock.lut_out:
                index = min(bisect.bisect_right(word_clock.lut_in, lux), len(word_clock.lut_out) - 1)
                brt = word_clock.lut_out[index]
                brightness_display = f"{lux}: {brt}"
            else:
                brightness_display = f"{lux}: {word_clock.strip.getBrightness()}"
                
            return jsonify({"brightness": brightness_display}), 200
        except Exception as e:
            logging.error(f"Failed to fetch brightness: {e}")
            return jsonify({"brightness": "Error reading sensor"}), 200
    
    # ================== MODE ROUTES ==================
    
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
    
    # ================== CALIBRATION ROUTES ==================
    
    @app.route("/calibration.html")
    def calibration_page():
        return render_template("calibration.html")
    
    @app.route("/get_calibration_data", methods=["GET"])
    def get_calibration_data():
        return jsonify({"lut_in": word_clock.lut_in, "lut_out": word_clock.lut_out})
    
    @app.route("/calibration/get_current_brightness", methods=["GET"])
    def get_current_brightness():
        try:
            return jsonify({"brightness": word_clock.strip.getBrightness()}), 200
        except Exception as e:
            logging.error(f"Failed to get current brightness: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/calibration/current_light", methods=["GET"])
    def get_current_light():
        try:
            if word_clock.light_sensor_type == "BH1750":
                lux = word_clock.light_sensor.measure_high_res()
            else:
                lux = abs(word_clock.light_sensor.get_current()['lux'])
            return jsonify({"lux": lux}), 200
        except Exception as e:
            logging.error(f"Failed to read light level: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/calibration/set_temporary_brightness", methods=["POST"])
    def set_temporary_brightness():
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
    
    @app.route("/calibration/save", methods=["POST"])
    def save_calibration():
        try:
            data = request.get_json()
            word_clock.lut_in = data.get("lut_in", [])
            word_clock.lut_out = data.get("lut_out", [])
            
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            with open(config_path, 'r+') as f:
                config = json.load(f)
                config['LUT_IN'] = word_clock.lut_in
                config['LUT_OUT'] = word_clock.lut_out
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logging.error(f"Failed to save calibration: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/calibration/cancel", methods=["POST"])
    def cancel_calibration():
        try:
            if hasattr(word_clock, 'original_brightness'):
                word_clock.strip.setBrightness(word_clock.original_brightness)
                word_clock.strip.show()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logging.error(f"Failed to cancel calibration: {e}")
            return jsonify({"error": str(e)}), 500
