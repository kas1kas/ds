## 1 install Raspberry Pi OS
(with raspberry pi imager)
- on a **Zero 2 W**: install Debian Bullseye **Rasberry Pi OS (Legacy, Lite 32 (bit)**
- on a **3B+**: you can also install Debian Bookworm **Rasberry Pi OS Lite 32 (bit)**
- set user pi and yourpassword
- set hostname
- set wifi
- enable ssh
## 2 start and configure
connect monitor, keyboard and mouse or use ssh to connect
```
sudo raspi-config
```
- interface options - enable I2C
- reboot
## 3 install packages
```
cd ~
sudo apt update
sudo apt install git python3-pip
```
- with bullseye, debian 11:
```
sudo pip3 install flask-restx rpi-ws281x python-tsl2591 buienradar
```
- with bookworm, debian 12
```
sudo pip3 install flask-restx rpi-ws281x python-tsl2591 buienradar --break-system-packages
```
## 4 install wordclock software
```
curl -L https://raw.githubusercontent.com/kas1kas/ds/main/install.sh | bash
```
## 5 install WiFi-connect
```
git clone https://github.com/kas1kas/wifi-connect.git
cd wifi-connect/scripts
sudo ./rpi_headless_wifi_install.sh
```
## 6 config and test
- See chapter below: **personalisation**
```
nano ~/.wordclock/config_loc.json
swk
```
## 7 Web interface
- connect via phone or computer with your web browser
- use the local IP-address (check your router) or use hostname (see step 1)
- try various options in the UI
## 8 reboot
The clock should start automatically within a minute

## Moving the Wordclock
When moving the wordclock to another location, you can connect to the new wifi network with the procedure below. If you give this clock to someone, make sure to give them this procedure.

## 1 Set IP address on new network

- make sure your phone is connected to your local WiFi network
- click/select Wi-Fi (icon) on your phone
- look for the wordclock wifi: **RPI-woordklok**
- select it (ignore messages about Internet may not be available)
- connect
- your phone is now connected to the WiFi of the wordclock
- start a web browser on your phone (chrome, edge, ...)
- type **192.168.42.1:8080**
### a page opens and shows your WiFi network
if not, click on the down arrow and your network
- type your password
- click connect
- the wordklock clock is now connected to your WiFi
- you phone also re-connects to your WiFi
- the correct time will appear on the wordclock after a while

## Personalisation
edit the file ~/.wordclock/config_loc.json. Do not add the comments between (). These are only here to explain.
```
{
    "VERSION": "x.yz",                       (do not edit or remove)
    "PURIST": true,                          (false/true: show HET IS / IT IS, or not)|
    "CALIBRATE": false,                      (true/false: show calibration menu or not)|
    "WOORDKLOK": "name",                     (enter your name or clock number)
    "LANGUAGE": "NL",                        (NL or EN supported at the moment)
    "GRID" : "11",                           (11: 11x10 or 16: 16x16 supported)
    "CLOCK_TYPE": "normal",                  (clockface after reboot: normal, random, dark, see menu while running)
    "RAND_COLOR": "blue",                    (random color: blue or orange supported)
    "LIGHT_INTERVAL": 1,                     (screen update speed, more is slower)
    "DEF_BRIGHTNESS" : 4,                    (brightness when no light sensor is detected)
    "BACKGROUND_COLOR": [0, 0, 0],           (all colors below: in R,G,B)
    "LETTER_ACTIVE_COLOR": [255, 255, 255],
    "DOT_ACTIVE_COLOR": [255, 255, 255],
    "DOT_INACTIVE_COLOR": [0,0,0],
    "DOT_DARK_COLOR": [100,0,0],
    "LUT_IN":  [0, 1,  5,  20,  80],         (Look up table to match light with your environment)
    "LUT_OUT": [1, 5, 40, 100, 160]          (translated version for LED brightness)
}
```















