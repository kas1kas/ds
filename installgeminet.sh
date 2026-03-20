#!/bin/bash
LOG_FILE=~/geminetlog.log
echo "--- Network Setup Started: $(date) ---" >> "$LOG_FILE"

# 1. Detect Gateway IP (Fritzbox)
# This finds the 'default' route and grabs the IP
GATEWAY_IP=$(ip route | grep default | awk '{print $3}' | head -n1)

if [ -z "$GATEWAY_IP" ]; then
    echo "Warning: Could not detect Gateway. Defaulting to 192.168.178.1" >> "$LOG_FILE"
    GATEWAY_IP="192.168.178.1"
else
    echo "Detected Gateway: $GATEWAY_IP" >> "$LOG_FILE"
fi

# 2. Hardware Specific Fixes (Zero 2W only)
MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\000')
if [[ "$MODEL" == *"Zero 2 W"* ]]; then
    echo "Applying Zero 2W Driver & Udev Fixes..." >> "$LOG_FILE"
    sudo bash -c 'echo "options brcmfmac roamoff=1 feature_disable=0x82000" > /etc/modprobe.d/brcmfmac.conf'
    sudo bash -c 'echo "ACTION==\"add\", SUBSYSTEM==\"net\", KERNEL==\"wlan0\", RUN+=\"/usr/sbin/iw dev wlan0 set power_save off\"" > /etc/udev/rules.d/81-wifi-powersave.rules'
fi

# 3. Global NetworkManager Fix
sudo bash -c 'cat <<EOF > /etc/NetworkManager/conf.d/disable-powersave.conf
[connection]
wifi.powersave = 2
EOF'

# 4. Create the "Heartbeat" Systemd Service
echo "Creating Heartbeat Service for $GATEWAY_IP..." >> "$LOG_FILE"

sudo bash -c "cat <<EOF > /etc/systemd/system/wifi-heartbeat.service
[Unit]
Description=Keep-alive Heartbeat to Gateway
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/ping -i 60 $GATEWAY_IP
Restart=always
RestartSec=10
StandardOutput=null

[Install]
WantedBy=multi-user.target
EOF"

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable -q wifi-heartbeat.service
sudo systemctl start wifi-heartbeat.service >> "$LOG_FILE" 2>&1

# 5. Set Wi-Fi to System-Wide (No login required)
# 5. Set Wi-Fi to System-Wide (UUID-based for Netplan/Trixie)
# 5. Set Wi-Fi to System-Wide (Active Interface Targeting)
echo "Setting Wi-Fi connections to System-Wide..." >> "$LOG_FILE"

# Get the UUID of the connection currently active on wlan0
# We use 'nmcli -t -f UUID,DEVICE connection show --active' 
# then grep for wlan0 to get the exact UUID in use.
#ACTIVE_UUID=$(LC_ALL=C nmcli -t -f UUID,DEVICE connection show --active 2>/dev/null | grep ":wlan0" | cut -d: -f1)
ACTIVE_UUID=$(LC_ALL=C nmcli -t -f UUID,DEVICE connection show --active 2>/dev/null | tr -d '\000' | grep ":wlan0" | cut -d: -f1)
if [ -z "$ACTIVE_UUID" ]; then
    echo "Warning: No active Wi-Fi UUID found on wlan0. Checking all wifi connections..." >> "$LOG_FILE"
    # Fallback: Just get any connection of type '802-11-wireless'
    #ACTIVE_UUID=$(LC_ALL=C nmcli -t -f UUID,TYPE connection show 2>/dev/null | grep ":802-11-wireless" | cut -d: -f1)
    ACTIVE_UUID=$(LC_ALL=C nmcli -t -f UUID,TYPE connection show 2>/dev/null | tr -d '\000' | grep ":802-11-wireless" | cut -d: -f1)
fi

if [ -n "$ACTIVE_UUID" ]; then
    for uuid in $ACTIVE_UUID; do
        echo "Successfully found and updating UUID: $uuid" >> "$LOG_FILE"
        sudo nmcli connection modify "$uuid" connection.permissions "" 802-11-wireless.powersave 2 >> "$LOG_FILE" 2>&1
        # Disable IPv6 to prevent the 45-second DHCP timeout
        sudo nmcli connection modify "$uuid" ipv6.method "disabled"
    done
else
    echo "Error: Could not identify any Wi-Fi connections to modify." >> "$LOG_FILE"
fi


echo "Network Setup Complete. Heartbeat active via Systemd." >> "$LOG_FILE"
