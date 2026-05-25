## 1 install Raspberry Pi OS
(with raspberry pi imager)
- the clock runs perfectly on a **Zero 2 W** a **3B+**
- install Debian Trixie **Rasberry Pi OS Lite 32 (bit)**
- set user pi and yourpassword
- set hostname
- aliset wifi
- enable ssh
## 2 start and configure
use ssh to connect
```
sudo raspi-config
```
- change default hostname
- reboot
## 3 install software
```
cd ~
curl -L https://raw.githubusercontent.com/kas1kas/ds/main/install_wk.sh | bash
```
## 4 config and reboot
- See chapter below: **personalisation**
```
-nano ~/.wordclock/config_loc.json
-reboot
```
## 5 install Comitup
```
https://github.com/davesteele/comitup
```
## 6 Web interface
- connect via phone or computer
- check your router for the ipaddress of the wordclock (something like 192.178.168.22)
- in your web browser type ipaddress:8080/
- save a shortcut or add to the homescreen

## 7 Automatic start at reboot
The clock starts automatically within a minute after reboot

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
edit the file ~/.wordclock/config_loc.toml.

```
At least: Select the correct Hardware setting.

  hardware = "11x10V"   # vertical LED strips,   11×10 grid
# hardware = "11x10H"   # horizontal LED strips, 11×10 grid
# hardware = "16x16V"   # LED matrix panel,      16×16 grid

The default is un commented, make sure it matches your wiring system
```























