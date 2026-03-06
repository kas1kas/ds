## 1 install Raspberry Pi OS
(with raspberry pi imager)
- on a **Zero 2 W**: install Debian Bullseye **Rasberry Pi OS (Legacy, Lite 32 (bit)**
- on a **3B+**: you can also install Debian Bookworm **Rasberry Pi OS Lite 32 (bit)**
- set user pi and yourpassword
- set hostname
- enable ssh
## 2 start and configure
use ssh to connect
```
sudo raspi-config
```
- interface options - enable I2C
- reboot
## 3 install packages
```
cd ~
sudo apt update
sudo apt install git python3-dev -y
```
- with debian 12 bookworm or debian 13 trixie
```
python3 -m venv wk_env
source wk_env/bin/activate
pip install flask-restx rpi-ws281x python-tsl2591 buienradar --index-url https://pypi.org/simple/
```
## 4 install wordclock software
```
cd ~
git clone "https://raw.githubusercontent.com/kas1kas/ds/main"
mkdir -p /home/pi/.wordclock
chmod 755 /home/pi/.wordclock
cp /home/pi/ds/config_loc.json /home/pi/.wordclock/config_loc.json
cp /home/pi/ds/alias.txt ~/.bash_aliases && source ~/.bash_aliases
```
## 6 config
- See chapter below: **personalisation**
```
nano ~/.wordclock/config_loc.json
swk
```





















