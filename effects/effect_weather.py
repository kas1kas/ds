import time
import math
import random
from effects.base_effect import BaseEffect

class EffectWeather(BaseEffect):
    """
    Weather effect for word clock.
    - Background color based on temperature (windy.com style).
    - Moving dark band based on wind speed/direction.
    - Raindrops falling top→bottom (panel space, y=0=top).
    - Time displayed in white on top.
    """
    name = "Weather"

    TEMP_STOPS = [
        (-20, (128,   0, 255)),
        (-15, ( 96,   0, 255)),
        (-10, ( 64,   0, 255)),
        ( -5, ( 32,   0, 255)),
        (  0, (  0,   0, 255)),
        (  5, (  0, 255,   0)),
        ( 10, ( 85, 255,   0)),
        ( 15, (170, 255,   0)),
        ( 20, (255, 255,   0)),
        ( 25, (255, 100,   0)),
        ( 30, (255,  50,   0)),
        ( 35, (255,   0,   0)),
        ( 39, (255,   0,   64)),
    ]

    DIRECTION_VECTORS = {
        'N':  ( 0,    1),
        'NE': ( 0.707,  0.707),
        'E':  ( 1,    0),
        'SE': ( 0.707, -0.707),
        'S':  ( 0,   -1),
        'SW': (-0.707, -0.707),
        'W':  (-1,    0),
        'NW': (-0.707,  0.707),
    }

    GAMMA = 1

    def __init__(self, word_clock, variant_id=None):
        super().__init__(word_clock, variant_id)

        self.offset    = 0.0
        self.last_time = time.time()

        self.wavelength     = 9.0
        self.amplitude      = 0.6
        self.band_sharpness = 5.0
        self.speed_scale    = 1

        self.precip_scale     = 0.15
        self.drop_speed_range = (1.5, 3.5)
        self.drop_color       = (64, 0, 255)
        self.max_drops        = 150
        self.drops            = []

        self.gamma_table = [int(pow(i / 255.0, self.GAMMA) * 255 + 0.5) for i in range(256)]

    def _gamma_correct(self, r, g, b):
        return (self.gamma_table[r], self.gamma_table[g], self.gamma_table[b])

    def _temperature_to_rgb(self, temp):
        if temp <= self.TEMP_STOPS[0][0]:
            return self.TEMP_STOPS[0][1]
        if temp >= self.TEMP_STOPS[-1][0]:
            return self.TEMP_STOPS[-1][1]
        for i in range(len(self.TEMP_STOPS) - 1):
            t1, c1 = self.TEMP_STOPS[i]
            t2, c2 = self.TEMP_STOPS[i + 1]
            if t1 <= temp <= t2:
                frac = (temp - t1) / (t2 - t1)
                return (
                    int(c1[0] + frac * (c2[0] - c1[0])),
                    int(c1[1] + frac * (c2[1] - c1[1])),
                    int(c1[2] + frac * (c2[2] - c1[2])),
                )
        return (0, 0, 0)

    def _wind_direction_to_vector(self, degrees):
        deg = degrees % 360
        if   deg < 22.5 or deg >= 337.5: key = 'N'
        elif deg < 67.5:                  key = 'NE'
        elif deg < 112.5:                 key = 'E'
        elif deg < 157.5:                 key = 'SE'
        elif deg < 202.5:                 key = 'S'
        elif deg < 247.5:                 key = 'SW'
        elif deg < 292.5:                 key = 'W'
        else:                             key = 'NW'
        return self.DIRECTION_VECTORS[key]

    def draw(self):
        now = time.time()
        dt  = min(now - self.last_time, 0.1)
        self.last_time = now

        temp      = self.word_clock.temperature
        speed     = self.word_clock.wind_speed
        direction = self.word_clock.wind_direction
        precip    = self.word_clock.precipitation
        bg_factor = self.word_clock.background_brightness_factor

        max_cols, max_rows = self.get_dimensions()
        base_color = self._temperature_to_rgb(temp)

        # --- 1. Temperature background + wind band ---
        # All coordinates are panel space: y=0=top, matches setcolor_x_y convention.
        self.offset += speed * self.speed_scale * dt
        dx, dy = self._wind_direction_to_vector(direction)

        for x in range(max_cols):
            for y in range(max_rows):
                proj     = x * dx + y * dy
                phase    = (proj - self.offset) / self.wavelength
                sin_val  = math.sin(2 * math.pi * phase)
                darkness = self.amplitude * ((0.5 + 0.5 * sin_val) ** self.band_sharpness)
                factor   = (1.0 - darkness) * bg_factor

                r = max(0, min(255, int(base_color[0] * factor)))
                g = max(0, min(255, int(base_color[1] * factor)))
                b = max(0, min(255, int(base_color[2] * factor)))
                r, g, b = self._gamma_correct(r, g, b)
                self.word_clock.setcolor_x_y(x, y, (r, g, b))

        # --- 2. Raindrops: spawn at y=0 (top), fall toward y=max_rows (bottom) ---
        # panel space y=0=top → increasing y = falling down. Correct for all hardware.
        if precip > 0:
            spawn_prob = min(precip * self.precip_scale * dt, 0.5)
            for col in range(max_cols):
                if random.random() < spawn_prob:
                    self.drops.append({
                        'col':   col,
                        'row':   0.0,
                        'speed': random.uniform(*self.drop_speed_range),
                    })

            new_drops = []
            for drop in self.drops:
                drop['row'] += drop['speed'] * dt
                if drop['row'] < max_rows:
                    new_drops.append(drop)
                    self.word_clock.setcolor_x_y(drop['col'], int(drop['row']),
                                                 self.drop_color)
            # Keep oldest drops first — they are closest to the bottom
            # and will disappear naturally. Trimming from the end (newest)
            # avoids visible pop-out of nearly-finished drops.
            if len(new_drops) > self.max_drops:
                new_drops = new_drops[:self.max_drops]
            self.drops = new_drops

        # --- 3. Clock words in white on top (also calls strip.show()) ---
        saved_letter = self.word_clock.letter_active_color
        saved_dot    = self.word_clock.dot_active_color
        self.word_clock.letter_active_color = (255, 255, 255)
        self.word_clock.dot_active_color    = (255, 255, 255)
        self.word_clock.update_clock()
        self.word_clock.letter_active_color = saved_letter
        self.word_clock.dot_active_color    = saved_dot
