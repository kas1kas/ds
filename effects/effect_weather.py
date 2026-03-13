import time
import math
import random
from effects.base_effect import BaseEffect

class EffectWeather(BaseEffect):
    """
    Weather effect for word clock.
    - Background color based on temperature (windy.com style).
    - Moving dark band (narrow and pronounced) based on wind speed/direction.
    - Raindrops falling, density controlled by precipitation.
    - Time displayed in white on top.
    """
    name = "Weather"

    # Temperature stops every 5°C for smooth gradient
    TEMP_STOPS = [
        (-20, (128,   0, 255)),   # purple
        (-15, ( 96,   0, 255)),
        (-10, ( 64,   0, 255)),
        ( -5, ( 32,   0, 255)),
        (  0, (  0,   0, 255)),   # blue
        (  5, (  0, 255,   0)),   # green
        ( 10, ( 85, 255,   0)),   # yellow green
        ( 15, (170, 255,   0)),
        ( 20, (255, 255,   0)),   # yellow
        ( 25, (255, 180,   0)),
        ( 30, (255, 100,   0)),   # orange
        ( 35, (255,  50,   0)),
        ( 40, (255,   0,   0))    # red
    ]

    # Wind direction to movement vector (dx, dy)
    # Adjusted for x increasing right-to-left (your display)
    DIRECTION_VECTORS = {
        'N':  (0, 1),                # north wind → blows south (down)
        'NE': (0.707, 0.707),        # northeast → blows southwest (left+down)
        'E':  (1, 0),                # east wind → blows west (left)
        'SE': (0.707, -0.707),       # southeast → blows northwest (left+up)
        'S':  (0, -1),               # south wind → blows north (up)
        'SW': (-0.707, -0.707),      # southwest → blows northeast (right+up)
        'W':  (-1, 0),               # west wind → blows east (right)
        'NW': (-0.707, 0.707)        # northwest → blows southeast (right+down)
    }

    GAMMA = 1

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)

        # Wind animation state
        self.offset = 0.0
        self.last_time = time.time()

        # Wind band parameters – adjusted for visibility
        self.wavelength = 9.0           # larger → fewer bands on screen
        self.amplitude = 0.6            # darkness factor (0.7 = 30% brightness min)
        self.band_sharpness = 5.0       # lower = smoother, wider band
        self.speed_scale = 1            # maps m/s to offset units per second

        # Precipitation parameters
        self.precip_scale = 0.15        # spawn probability per column per second per mm/h
        self.drop_speed_range = (1.5, 3.5)  # rows per second
        self.drop_color = (64, 0, 255)   # purple
        self.max_drops = 150             # prevent overflow
        self.drops = []                  # list of active drops: {'col': c, 'row': r, 'speed': s}

        # Gamma correction lookup table
        self.gamma_table = [int(pow(i/255.0, self.GAMMA) * 255 + 0.5) for i in range(256)]

    def _gamma_correct(self, r, g, b):
        return (self.gamma_table[r], self.gamma_table[g], self.gamma_table[b])

    def _temperature_to_rgb(self, temp):
        """Convert temperature to RGB using windy.com style gradient (5° steps)."""
        if temp <= self.TEMP_STOPS[0][0]:
            return self.TEMP_STOPS[0][1]
        if temp >= self.TEMP_STOPS[-1][0]:
            return self.TEMP_STOPS[-1][1]

        for i in range(len(self.TEMP_STOPS)-1):
            t1, c1 = self.TEMP_STOPS[i]
            t2, c2 = self.TEMP_STOPS[i+1]
            if t1 <= temp <= t2:
                frac = (temp - t1) / (t2 - t1)
                r = int(c1[0] + frac * (c2[0] - c1[0]))
                g = int(c1[1] + frac * (c2[1] - c1[1]))
                b = int(c1[2] + frac * (c2[2] - c1[2]))
                return (r, g, b)
        return (0, 0, 0)

    def _wind_direction_to_vector(self, degrees):
        """Convert wind direction (0-360) to a movement vector (dx, dy)."""
        deg = degrees % 360
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
        else:
            key = 'NW'
        return self.DIRECTION_VECTORS[key]

    def draw(self):
        now = time.time()
        dt = min(now - self.last_time, 0.1)  # cap large gaps
        self.last_time = now

        # Read live weather data from word_clock
        temp = self.word_clock.temperature
        speed = self.word_clock.wind_speed
        direction = self.word_clock.wind_direction
        precip = self.word_clock.precipitation

        # Clear screen based on config
        self.clear_screen()

        # Get dimensions based on config
        max_cols, max_rows = self.get_dimensions()

        # 1. Background color from temperature
        base_color = self._temperature_to_rgb(temp)

        # Apply current background brightness dynamically
        # Debug: print values occasionally
        if random.random() < 0.01:  # ~1% of frames
            bg_factor = self.word_clock.background_brightness_factor
            print(f"BG Factor: {bg_factor}, Base color: {base_color}")

        bg_factor = self.apply_background_brightness(base_color)

        # Debug: compare colors
        if random.random() < 0.01:
            print(f"After dim: {bg_color}")

        # 2. Wind movement update
        self.offset += speed * self.speed_scale * dt

        # 3. Get movement vector from wind direction
        dx, dy = self._wind_direction_to_vector(direction)

        # 4. Set all pixels to temperature + wind band
        for x in range(max_cols):
            for y in range(max_rows):
                proj = x * dx + y * dy
                phase = (proj - self.offset) / self.wavelength
                sin_val = math.sin(2 * math.pi * phase)
                darkness_factor = (0.5 + 0.5 * sin_val) ** self.band_sharpness
                darkness = self.amplitude * darkness_factor
                factor = 1.0 - darkness

                r = int(base_color[0] * factor)
                g = int(base_color[1] * factor)
                b = int(base_color[2] * factor)

                # Apply background dimming AFTER wind effect
                r = int(r * bg_factor)
                g = int(g * bg_factor)
                b = int(b * bg_factor)
                                
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))

                # Gamma correction
                r, g, b = self._gamma_correct(r, g, b)
                self.word_clock.setcolor_x_y(x, y, (r, g, b))

        # 5. Precipitation: spawn and draw grey drops
        if precip > 0:
            # Spawn new drops (probability per column per second)
            spawn_prob = precip * self.precip_scale * dt
            # Clamp to avoid huge bursts
            if spawn_prob > 0.5:
                spawn_prob = 0.5

            for col in range(max_cols):
                if random.random() < spawn_prob:
                    self.drops.append({
                        'col': col,
                        'row': 0.0,
                        'speed': random.uniform(*self.drop_speed_range)
                    })

            # Update and draw existing drops
            new_drops = []
            for drop in self.drops:
                drop['row'] += drop['speed'] * dt
                if drop['row'] < max_rows:
                    new_drops.append(drop)
                    row_int = int(drop['row'])
                    # Draw drop (grey)
                    self.word_clock.setcolor_x_y(drop['col'], row_int, self.drop_color)
                # else drop falls off screen → not kept

            self.drops = new_drops

            # Limit total drops to avoid memory issues
            if len(self.drops) > self.max_drops:
                self.drops = self.drops[-self.max_drops:]

        # 6. Draw time in white on top (this also calls strip.show())
        original_color = self.word_clock.letter_active_color
        original_dot = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = original_color
        self.word_clock.dot_active_color = original_dot
