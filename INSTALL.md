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
## 5 install Comitup
```
https://github.com/davesteele/comitup
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

- use your phone to set the Wifi on the wordclock:
- click/select Wi-Fi (icon) on your phone
- look for the wordclock wifi: **comitup-xxx**
- connect
- Select Sign in to comitup-xxx
- Choose WiFi Connection
- enter your password
- click on the CONNECT button
- the wordklock clock is now connected to your WiFi
- you phone automatically re-connects to your WiFi
- the correct time will appear on the wordclock after a while
- in case the above does not show the WiFi configurator:
- start a web browser on your phone (chrome, edge, ...)
- type **10.41.0.1**
- proceed as mentioned above

## Personalisation
edit the file ~/.wordclock/config_loc.json. Do not add the comments between (). These are only here to explain.
```
{
    "VERSION": "7.xy",
    "PURIST": true,
    "CALIBRATE": false, 
    "WOORDKLOK": "yourname",
    "LANGUAGE": "NL",
    "GRID" : "11",
    "DEFAULT_EFFECT": "matrix",
    "RAND_COLOR": "blue",
    "WEATHER_ENABLED": true,
    "WEATHER_LAT": 51.5382,
    "WEATHER_LON": 5.3679,
    "WEATHER_UPDATE_INTERVAL": 300,
    "LIGHT_INTERVAL": 1,
    "DEF_BRIGHTNESS" : 4,
    "BACKGROUND_COLOR": [0, 0, 0],
    "LETTER_ACTIVE_COLOR": [255, 255, 255],
    "DOT_ACTIVE_COLOR": [255, 255, 255],
    "DOT_INACTIVE_COLOR": [0,0,0],
    "DOT_DARK_COLOR": [100,0,0],
    "LUT_IN":  [0, 1,  5,  20,  80],
    "LUT_OUT": [1, 5, 40, 100, 160]
}
```


















