__version__ = "7.45"
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
    @app.route("/show_brightness", methods=["GET"])
    def show_brightness():
        try:
            lux = round(word_clock._lux, 2)
            brightness = round(word_clock.last_brightness, 1)
            return jsonify({"brightness": f"{lux}:  {brightness}"}), 200
        except Exception as e:
            logging.error(f"Failed to fetch brightness: {e}")
            return jsonify({"brightness": "Error reading sensor"}), 500  
            
    # ================== Back_ground BRIGHTNESS ROUTES ================
    @app.route('/set_background_brightness', methods=['POST'])
    def set_background_brightness():
        data = request.json
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
