#v1.1
from python_tsl2591 import tsl2591
from smbus2 import SMBus
import sys
import bisect
import argparse
import json
import os
import logging

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global variable for last brightness, initialized to None.
# This will store the brightness value from the previous successful update.
last_brightness = None

def bargraph(s, p, r):
    """
    Inserts a character 'r' at position 'p' in string 's' to create a bar graph.
    """
    return s[:p] + r + s[p+1:]

def update_brightness(lut_in, lut_out, light_sensor, light_sensor_type):
    """
    Calculates the new brightness based on ambient light (lux) readings
    and applies linear interpolation and exponential smoothing.

    Args:
        lut_in (list): List of input lux values for calibration.
        lut_out (list): List of corresponding output brightness values for calibration.
        light_sensor (object): The initialized light sensor object (TSL2591 or BH1750).
        light_sensor_type (str): The type of light sensor ("BH1750" or other, defaulting to TSL2591).

    Returns:
        int: The calculated and smoothed brightness value. Returns the last known
             brightness or 0 if an error occurs during measurement.
    """
    global last_brightness # Declare intent to modify the global variable

    try:
        # Read lux value based on sensor type
        if light_sensor_type == "BH1750":
            # Assuming light_sensor is an instance of the BH1750 sensor class
            lux = light_sensor.measure_high_res()
        else:
            # Default to TSL2591 if not BH1750 or type is unspecified
            light_data = light_sensor.get_current()
            lux = abs(light_data['lux'])

        # Perform smooth linear interpolation between calibration points
        if len(lut_in) >= 2:
            # Find the segment where the current lux value falls
            idx = bisect.bisect_left(lut_in, lux) - 1
            # Ensure index is within valid bounds for interpolation
            idx = max(0, min(idx, len(lut_in) - 2))

            # Get the two calibration points for interpolation
            x0, x1 = lut_in[idx], lut_in[idx+1]
            y0, y1 = lut_out[idx], lut_out[idx+1]

            if x1 != x0:  # Avoid division by zero for interpolation
                brightness = y0 + (y1 - y0) * (lux - x0) / (x1 - x0)
            else:
                # If x0 and x1 are the same, brightness is simply y0
                brightness = y0
        elif len(lut_in) == 1:
            # If only one calibration point, use its output brightness
            brightness = lut_out[0]
        else:
            # If no calibration points, log a warning and return a default brightness
            brightness = 0
            logging.warning("No calibration points found in LUT_IN/LUT_OUT. Returning default brightness (0).")

        # Apply exponential smoothing for smoother transitions
        # This check ensures smoothing only happens after the first successful reading
        if last_brightness is not None:
            alpha = 0.3  # Smoothing factor (0-1, higher = more smoothing)
            brightness = alpha * last_brightness + (1 - alpha) * brightness

        # Update the global last_brightness for the next iteration
        last_brightness = brightness
        return int(brightness) # Return the calculated integer brightness
    except Exception as e:
        # Log the error if brightness update fails
        logging.error(f"Failed to update brightness: {e}")
        # Return the last known brightness, or 0 if it's the first error encountered
        return int(last_brightness) if last_brightness is not None else 0


def load_config(config_file):
    """
    Loads configuration from a JSON file.

    Args:
        config_file (str): The name of the configuration file (e.g., "config.json").

    Returns:
        dict: The loaded configuration dictionary, or None if an error occurs.
    """
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
        print(f"An unexpected error occurred while loading config: {e}")
        return None


if __name__ == '__main__':
    # Load configuration
    config = load_config("config.json")
    if config is None:
        sys.exit(1) # Exit if config loading failed

    # Retrieve configuration values
    woordklok = config.get("WOORDKLOK")
    light_sensor_type = config.get("LIGHT_SENSOR")
    print(f"woordklok: {woordklok}")
    print(f"-------")

    # Get LUT (Look-Up Table) values, defaulting to empty lists if not found
    # This ensures that .get() on a potentially None object doesn't cause an error
    lut_in = config.get("LUT_IN", {}).get(woordklok, [])
    lut_out = config.get("LUT_OUT", {}).get(woordklok, [])

    # Validate that LUT_IN and LUT_OUT have matching lengths for interpolation
    if len(lut_in) != len(lut_out):
        logging.error("Configuration Error: LUT_IN and LUT_OUT must have the same number of calibration points.")
        sys.exit(1)

    logging.info(f"Sensor   : {light_sensor_type}")
    logging.info(f"in :{lut_in}")
    logging.info(f"uit:{lut_out}")
  

    # Define constants for graph and scaling
    lineaal = "├───┴───┴───┴───┴───┼───┴───┴───┴───┴───┤"
    luxmax = 200
    brtmax = 250
    luxscalemax = 40
    brtscalemax = 40
    CURSOR_UP = "\x1b[2A" # ANSI escape code to move cursor up 2 lines

    # Initialize light sensor based on the configured type
    light_sensor = None
    if light_sensor_type == "BH1750":
        try:
            light_sensor = BH1750()
        except Exception as e:
            logging.error(f"Failed to initialize BH1750 sensor: {e}. Ensure sensor is connected and accessible.")
            sys.exit(1)
    else:
        # Default to TSL2591 if no specific type or an unknown type is given
        try:
            light_sensor = tsl2591()
        except Exception as e:
            logging.error(f"Failed to initialize TSL2591 sensor: {e}. Ensure sensor is connected and accessible.")
            sys.exit(1)

    # Print calibration points for user reference
    in_str = ", ".join(f"{x:>4}" for x in lut_in)
    out_str = ", ".join(f"{x:>4}" for x in lut_out)
    print(f"In : {in_str}")
    print(f"Out: {out_str}")
    print("----------------------------------------")

    # Main loop for continuous brightness updates and display
    while True:
        # Get the new brightness value from the update_brightness function
        # Pass all necessary parameters to make the function self-contained
        newbright = update_brightness(lut_in, lut_out, light_sensor, light_sensor_type)

        # Read the current lux value for display purposes (separate from brightness calculation)
        try:
            if light_sensor_type == "BH1750":
                lux = light_sensor.measure_high_res()
            else:
                light_data = light_sensor.get_current()
                lux = abs(light_data['lux'])
        except Exception as e:
            logging.error(f"Failed to read lux for display: {e}")
            lux = 0 # Default lux to 0 if reading fails to prevent further errors

        # Calculate positions for bar graphs
        x = int(lux * (luxscalemax / luxmax))
        y = int(newbright * (brtscalemax / brtmax))
        graphlux = bargraph(lineaal, x, "■")
        graphbrt = bargraph(lineaal, y, "■")

        # Format lux value for display based on its magnitude
        format_str = (
            "%5.0f" if lux >= 100 else  # No decimals for 100-999
            "%5.1f" if lux >= 10 else    # 1 decimal for 10-99
            "%5.2f" if lux >= 1 else     # 2 decimals for 1-9
            "%5.3f"                      # 3 decimals for < 1
        )
        formatted_lux = format_str % lux

        # Remove leading zero for values less than 1 (e.g., "0.123" becomes ".123")
        if lux < 1 and formatted_lux.strip().startswith("0"):
           formatted_lux = formatted_lux.strip()[1:]

        # Print lux and its bar graph
        print("L: " + formatted_lux, end="")
        print(graphlux, luxmax, " ")

        # Print brightness and its bar graph
        print("B: %5d" % newbright, end="")
        print(graphbrt, brtmax)

        # Move cursor up to overwrite previous lines in the terminal
        sys.stdout.write(CURSOR_UP)
