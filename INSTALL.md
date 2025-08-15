## 1 install Raspberry Pi OS
(with raspberry pi imager)
- on a **Zero 2 W**: install Debian Bullseye **Rasberry Pi OS (Legacy, Lite 32 (bit)**
- on a **3B+**: you can also install Debian Bookworm **Rasberry Pi OS Lite 32 (bit)**
- enable ssh
- set hostname
- set wifi
## 2 start and configure
- sudo raspi-config
- interface options - enable I2C
- reboot
## 3 install packages
- make sure you are in: /home/pi
- sudo apt update
- sudo apt install git python3-pip
> with bullseye, debian 11:
- sudo pip3 install flask-restx rpi-ws281x python-tsl2591
> with bookworm, debian 12
- sudo pip3 install flask-restx rpi-ws281x python-tsl2591 --break-system-packages
## 4 install wordclock software
- git clone https://github.com/kas1kas/ds.git
- ds/setwk.sh
- exec bash
## 5 install WiFi-connect
- git clone https://github.com/kas1kas/wifi-connect.git
- cd wifi-connect/scripts
- sudo ./rpi_headless_wifi_install.sh
## 6 config and test
- cd /home/pi/ds
- edit the config file: woordklok name, matrix, lut
- swk (start wordclock alias for: sudo python3 /home/pi/ds/wk.py
## 7 reboot
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




