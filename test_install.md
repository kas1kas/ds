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
sudo apt update -y
sudo apt install git python3-dev -y
```
## 4 install wordclock software
```
cd ~
git clone "https://github.com/kas1kas/ds/"
mkdir -p /home/pi/.wordclock
chmod 755 /home/pi/.wordclock
cp /home/pi/ds/config_loc.json /home/pi/.wordclock/config_loc.json
cp /home/pi/ds/alias.txt ~/.bash_aliases && source ~/.bash_aliases
log "Setting up new crontab"
echo "@reboot sudo /home/pi/wk_env/bin/python /home/pi/ds/wk.py > /home/pi/cron_log.txt 2>&1" | crontab -
```
## 5 install python v_env for wordclock
```
python3 -m venv wk_env
source wk_env/bin/activate
pip install flask-restx rpi-ws281x python-tsl2591 buienradar --index-url https://pypi.org/simple/
```
## 6 config
- See chapter below: **personalisation**
```
nano ~/.wordclock/config_loc.json
swk
```





















