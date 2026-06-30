#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = "7.63"
import time
from lux_client import get_lux

RED =    '\033[91m'
GREEN =  '\033[92m'
BLUE =   '\033[94m'
YELLOW = '\033[93m'

RESET =  '\033[0m'
MAX_LUX = 120.0
BARLONG = 50

while True:
    lux = get_lux()
    
    if lux < 0:
        lux_str = " ERR"
        bar = "?" * BARLONG
        color = RED
    else:
        lux_str = f"{lux:6.3f}"
        signal = int((min(lux, MAX_LUX) / MAX_LUX) * BARLONG)
        bar = "█" * signal + "░" * (BARLONG - signal)
        
        # Color based on value
        if lux < 1:
            color = BLUE
        elif lux < 10:
            color = GREEN
        elif lux < 80:
            color = YELLOW
        else:
            color = RED
    
    print(f"\033[2K\r{color}{lux_str}  {bar}{RESET}", end='', flush=True)
    time.sleep(1)
