## 1 install Raspberry Pi OS
(with raspberry pi imager)
- the clock runs perfectly on a **Zero W, Zero 2W** or **3B+**
- install Debian Trixie **Rasberry Pi OS Lite 32 (bit)**
- set user pi and yourpassword
- set hostname
- set wifi
- enable ssh

## 2 install software
```
cd ~
curl -L https://raw.githubusercontent.com/kas1kas/ds/unify/install_wk.sh | bash
```
## 3 config and reboot
- **personalisation**
- edit the file ~/.wordclock/config_loc.toml
- The default hardware and wiring is un-commented, make sure it matches your wiring system
- Select only the correct line
```
nano ~/.wordclock/config_loc.toml
```

```
  hardware = "11x10V"   # vertical LED strips,   11×10 grid
# hardware = "11x10H"   # horizontal LED strips, 11×10 grid
# hardware = "16x16V"   # LED matrix panel,      16×16 grid
```
- sudo password only once: add Defaults line
```
sudo visudo
```
```
Defaults        env_reset, timestamp_timeout=-1
```
- reboot the system!
- The clock starts automatically within a minute after reboot (2 minutes for a Zero W)

## 4 Wordklok web interface
- check your router for the ipaddress of the wordclock (example 192.178.168.22)
- You can also use the hostname (example: woordklok13)
- in your web browser type ipaddress:8080/ or woordklok13:8080/
- save a shortcut or add to the homescreen

## 5 OPTIONAL: install Comitup
```
https://github.com/davesteele/comitup
```
### Moving the Wordclock
When moving the wordclock to another location, you can connect to the new wifi network with the procedure below. If you give this clock to someone, make sure to give them this procedure.

### Set IP address on new network

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























