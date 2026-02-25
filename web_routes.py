import logging
import bisect
import time
import os
import json
import subprocess
import re
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

# ================== WIFI MANAGEMENT ROUTES ==================

@app.route("/wifi")
def wifi_page():
    """Serve the WiFi management page"""
    return render_template("wifi.html")

@app.route("/wifi/scan", methods=["GET"])
def wifi_scan():
    """Scan for available WiFi networks"""
    try:
        # Run nmcli to scan for networks
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        networks = []
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 3 and parts[0]:  # SSID not empty
                        networks.append({
                            'ssid': parts[0],
                            'signal': parts[1],
                            'security': parts[2] if parts[2] else 'None'
                        })
        
        return jsonify({"status": "success", "networks": networks}), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Scan timed out"}), 500
    except Exception as e:
        logging.error(f"WiFi scan failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/wifi/connect", methods=["POST"])
def wifi_connect():
    """Connect to a WiFi network"""
    try:
        data = request.get_json()
        ssid = data.get("ssid")
        password = data.get("password")
        
        if not ssid:
            return jsonify({"error": "SSID is required"}), 400
        
        # Build command based on whether password is provided
        if password:
            cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
        else:
            # Open network - try without password
            cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid]
        
        # Run connection command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logging.info(f"Successfully connected to {ssid}")
            return jsonify({"status": "success", "message": f"Connected to {ssid}"}), 200
        else:
            error_msg = result.stderr or "Connection failed"
            return jsonify({"error": error_msg}), 400
            
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Connection timed out"}), 500
    except Exception as e:
        logging.error(f"WiFi connection failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/wifi/current", methods=["GET"])
def wifi_current():
    """Get current WiFi connection status"""
    try:
        # Get active connections
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'TYPE,NAME,DEVICE', 'con', 'show', '--active'],
            capture_output=True,
            text=True
        )
        
        current_wifi = None
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('wifi:'):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_wifi = parts[1]  # Connection name (SSID)
                        break
        
        return jsonify({"status": "success", "current_ssid": current_wifi}), 200
        
    except Exception as e:
        logging.error(f"Failed to get current WiFi: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/wifi/forget", methods=["POST"])
def wifi_forget():
    """Forget a saved WiFi network"""
    try:
        data = request.get_json()
        ssid = data.get("ssid")
        
        if not ssid:
            return jsonify({"error": "SSID is required"}), 400
        
        # Find connection by name
        result = subprocess.run(
            ['nmcli', 'con', 'show'],
            capture_output=True,
            text=True
        )
        
        # Try to delete the connection
        del_result = subprocess.run(
            ['nmcli', 'con', 'delete', ssid],
            capture_output=True,
            text=True
        )
        
        if del_result.returncode == 0:
            return jsonify({"status": "success", "message": f"Forgot network {ssid}"}), 200
        else:
            return jsonify({"error": del_result.stderr}), 400
            
    except Exception as e:
        logging.error(f"Failed to forget network: {e}")
        return jsonify({"error": str(e)}), 500

    
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
        
        # Create list of available effects for dropdown
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
            available_effects=available_effects
        )
    # ================== WIFI MANAGEMENT ROUTES ===============end
    
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

    @app.route("/get_effect_settings", methods=["GET"])
    def get_effect_settings():
        """Get HTML for current effect's settings"""
        try:
            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect and hasattr(current_effect, 'get_settings_template'):
                settings_html = current_effect.get_settings_template()
                return jsonify({"settings_html": settings_html}), 200
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
            
            if 'language' in data:
                word_clock.update_language(data['language'])
            
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

    @app.route('/matrix/set_speed', methods=['POST'])
    def set_matrix_speed():
        try:
            data = request.get_json()
            speed = data.get('speed')
            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect and hasattr(current_effect, 'set_speed'):
                current_effect.set_speed(speed)
                return jsonify({"status": "success"}), 200
            return jsonify({"error": "Not matrix effect"}), 400
        except Exception as e:
            logging.error(f"Failed to set matrix speed: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/matrix/set_trail', methods=['POST'])
    def set_matrix_trail():
        try:
            data = request.get_json()
            length = data.get('length')
            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect and hasattr(current_effect, 'set_trail'):
                current_effect.set_trail(length)
                return jsonify({"status": "success"}), 200
            return jsonify({"error": "Not matrix effect"}), 400
        except Exception as e:
            logging.error(f"Failed to set matrix trail: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/rainbow/set_effect', methods=['POST'])
    def set_rainbow_sub_effect():
        """Set the rainbow pattern sub-effect"""
        try:
            data = request.get_json()
            sub_effect = data.get('sub_effect')
            
            current_effect = word_clock.effects.get(word_clock.current_effect_id)
            if current_effect and hasattr(current_effect, 'set_sub_effect'):
                if current_effect.set_sub_effect(sub_effect):
                    return jsonify({"status": "success"}), 200
                else:
                    return jsonify({"error": "Invalid sub-effect"}), 400
            else:
                return jsonify({"error": "Current effect does not support sub-effects"}), 400
                
        except Exception as e:
            logging.error(f"Failed to set rainbow sub-effect: {e}")
            return jsonify({"error": str(e)}), 500

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

    @app.route("/calibration.html")
    def calibration_page():
        """Serve the calibration interface"""
        return render_template("calibration.html")

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

    @app.route("/calibration/cancel", methods=["POST"])
    def cancel_calibration():
        """Cancel calibration and restore original settings"""
        try:
            if hasattr(word_clock, 'original_brightness'):
                word_clock.strip.setBrightness(word_clock.original_brightness)
                word_clock.strip.show()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logging.error(f"Failed to cancel calibration: {e}")
            return jsonify({"error": str(e)}), 500
