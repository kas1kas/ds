import time
import math
from effects.base_effect import BaseEffect

class EffectWeather(BaseEffect):
    """
    Weather effect for word clock.
    Background color based on temperature (windy.com style).
    Moving dark band based on wind speed and direction.
    Time displayed in white on top.
    """
    name = "Weather"

    # Temperature stops every 5°C for smooth gradient
    # Colors interpolated from the original windy.com scheme:
    # purple (-20), blue (0), green (10), yellow (20), orange (30), red (40)
    TEMP_STOPS = [
        (-20, (128, 0, 255)),   # purple
        (-15, (96, 0, 255)),
        (-10, (64, 0, 255)),
        (-5,  (32, 0, 255)),
        (0,   (0, 0, 255)),     # blue
        (5,   (0, 128, 255)),
        (10,  (0, 255, 0)),     # green
        (15,  (128, 255, 0)),
        (20,  (255, 255, 0)),   # yellow
        (25,  (255, 210, 0)),
        (30,  (255, 165, 0)),   # orange
        (35,  (255, 83, 0)),
        (40,  (255, 0, 0))      # red
    ]

    # Wind direction to movement vector (dx, dy)
    # Input: wind direction in degrees (0° = north wind, blowing south)
    # Movement direction is the direction the band moves (south for north wind)
    # We map 8 compass points.
    DIRECTION_VECTORS = {
        'N':  (0, 1),    # north wind -> band moves south
        'NE': (-0.707, 0.707),  # northeast wind -> band moves southwest
        'E':  (-1, 0),   # east wind -> band moves west
        'SE': (-0.707, -0.707), # southeast wind -> band moves northwest
        'S':  (0, -1),   # south wind -> band moves north
        'SW': (0.707, -0.707),  # southwest wind -> band moves northeast
        'W':  (1, 0),    # west wind -> band moves east
        'NW': (0.707, 0.707)    # northwest wind -> band moves southeast
    }

    # Gamma correction for WS2812B LEDs (human eye perceives non‑linearly)
    GAMMA = 2.2

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)
        # Define local Weather parameters (must be updated by main program)
        self.temperature = 0.0
        self.precipitation = 0.0
        self.wind_speed = 0.0
        self.wind_direction = 0.0

        # Animation state
        self.offset = 0.0          # moving phase for wind band
        self.last_time = time.time()

        # Band parameters
        self.wavelength = 7.0       # 3   distance between band peaks (in grid cells) 
        self.amplitude = 0.5        # 0.3 max darkness (0-1), so brightness factor 0.7-1.0
        self.speed_scale = 0.5      # maps m/s to offset units per second

        # Pre‑compute gamma correction lookup table for speed
        self.gamma_table = [int(pow(i/255.0, self.GAMMA) * 255 + 0.5) for i in range(256)]

    def _gamma_correct(self, r, g, b):
        """Apply gamma correction using lookup table."""
        return (self.gamma_table[r], self.gamma_table[g], self.gamma_table[b])

    def _temperature_to_rgb(self, temp):
        """Convert temperature to RGB using windy.com style gradient (5° steps)."""
        # Clamp to range of stops
        if temp <= self.TEMP_STOPS[0][0]:
            return self.TEMP_STOPS[0][1]
        if temp >= self.TEMP_STOPS[-1][0]:
            return self.TEMP_STOPS[-1][1]

        # Find interval
        for i in range(len(self.TEMP_STOPS)-1):
            t1, c1 = self.TEMP_STOPS[i]
            t2, c2 = self.TEMP_STOPS[i+1]
            if t1 <= temp <= t2:
                # Linear interpolation
                frac = (temp - t1) / (t2 - t1)
                r = int(c1[0] + frac * (c2[0] - c1[0]))
                g = int(c1[1] + frac * (c2[1] - c1[1]))
                b = int(c1[2] + frac * (c2[2] - c1[2]))
                return (r, g, b)

        # Fallback (should not happen)
        return (0, 0, 0)

    def _wind_direction_to_vector(self, degrees):
        """Convert wind direction (0-360) to a movement vector (dx, dy)."""
        # Normalize to 0-360
        deg = degrees % 360
        # Determine compass point
        if deg < 22.5 or deg >= 337.5:
            key = 'N'
        elif 22.5 <= deg < 67.5:
            key = 'NE'
        elif 67.5 <= deg < 112.5:
            key = 'E'
        elif 112.5 <= deg < 157.5:
            key = 'SE'
        elif 157.5 <= deg < 202.5:
            key = 'S'
        elif 202.5 <= deg < 247.5:
            key = 'SW'
        elif 247.5 <= deg < 292.5:
            key = 'W'
        else:  # 292.5 <= deg < 337.5
            key = 'NW'

        return self.DIRECTION_VECTORS[key]

    def draw(self):
        """Main draw routine."""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # Use current weather values
        temp = self.temperature
        speed = self.wind_speed
        direction = self.wind_direction

        # 1. Base background color from temperature
        base_color = self._temperature_to_rgb(temp)

        # 2. Wind movement update
        self.offset += speed * self.speed_scale * dt

        # 3. Get movement vector from wind direction
        dx, dy = self._wind_direction_to_vector(direction)

        # 4. Compute darkness factor for each cell and set color
        for x in range(self.word_clock.columns):
            for y in range(self.word_clock.rows):
                # Project cell onto movement direction
                proj = x * dx + y * dy
                # Compute phase
                phase = (proj - self.offset) / self.wavelength
                # Sine wave in range [-1, 1] -> map to [0,1] for darkness
                darkness = self.amplitude * (0.5 + 0.5 * math.sin(2 * math.pi * phase))
                factor = 1.0 - darkness

                # Apply factor to base color
                r = int(base_color[0] * factor)
                g = int(base_color[1] * factor)
                b = int(base_color[2] * factor)
                # Clamp to 0-255 (just in case)
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))

                # Apply gamma correction for WS2812B
                r, g, b = self._gamma_correct(r, g, b)

                self.word_clock.setcolor_x_y(x, y, (r, g, b))

        # 5. Draw time in white on top
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        # Restore original colors (for other effects)
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot

    def update_weather(self, temperature, precipitation, wind_speed, wind_direction):
        """Update weather parameters from the main program."""
        self.temperature = temperature
        self.precipitation = precipitation
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
