# Woordklok ds
## Workclock software
Software to drive your matrix wordclock

## Hardware
- Raspberry Pi **3B+** or Raspberri Pi **Zero2W**
- LED string WS281B or WS218B 16x16 LED panel
- lightsensor: optional but strongly reccomended: BH1750 or TSL 2591
- wordclock frame
- wordclock letterplate one per language

## Software
- Python3 + html
- Remote control via the integrated webapp.
- Configuration with a json file for persoanl settings and light sensor calibration.
- See the INSTALL.md for the software install and configuration.

## Build 
### 1 original
- cut the ledstrip; you need 11 pieces of 10 leds and 4 single leds
- place the wordclock frame with the face side on the table;  you will be working on the back side
- arrange the strings as 11 columns on your wordclock frame starting on the right of the frame
- place one single led at each corner
- solder the led power and signal connectors together. start with the led in the lower left corner, connect this to the led in the upper left corner, then connect to the top of the left most ledstring. At the bottom, connect the first string to the second, at the top connect the second to the third, etc end with the two leds in the corners.
- connect the leds to a 5 volt power source and the signal line to pin x of the raspberry Pi
- a USB-C Breakout Board ideal for the 5V
- connect the light sensor to the raspberry pi header as shown in the diagram.
  
### 2 mini
- you only need to connect the leds and the light sensor as described above

## The frame and letterplate
### 1 original
- MDF frame
- Letterplate: wood, aluminium, (colored) acryl or any other 2 - 3 mm flat material
- Letterplate swappable: other colors, different language. Mounted with magnets.

### 2 mini
- Cut out from one piece of massive hardwood by CNC.
- 3D printed light containment grid.

## Diagrams
in /support
