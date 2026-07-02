#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = "7.71"
import sys
import time
import select
import tty
import termios
from lux_client import get_lux

RED =    '\033[91m'
GREEN =  '\033[92m'
BLUE =   '\033[94m'
YELLOW = '\033[93m'

RESET =  '\033[0m'
MAX_LUX = 120.0
BARLONG = 50

def key_pressed():
    """Returns True if there is a character waiting in the stdin buffer."""
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

# Save the current terminal settings so we can restore them later
old_settings = termios.tcgetattr(sys.stdin)

try:
    # Put terminal into cbreak mode (read keys instantly without waiting for Enter)
    tty.setcbreak(sys.stdin.fileno())
    
    print("Measuring light. Press 'q' to stop...\n")

    while True:
        # Check if user pressed 'q'
        if key_pressed():
            key = sys.stdin.read(1)
            if key.lower() == 'q':
                print("\nLoop stopped cleanly by user.")
                break

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
        
        # Split the 1-second delay into 10 smaller chunks to keep 
        # the program highly responsive to keypresses
        for _ in range(10):
            if key_pressed():
                break
            time.sleep(0.1)

finally:
    # Always restore the terminal settings back to normal
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
