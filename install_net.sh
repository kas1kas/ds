# ------------------------------------------------------------------------------
# Step 1b - Network configuration (mDNS, IPv6, WiFi power management)
# ------------------------------------------------------------------------------
log "STEP 1b: Configuring network (mDNS, IPv6, WiFi power management)..."

log "Disabling WiFi power management..."
sudo iwconfig wlan0 power off
sudo tee /etc/NetworkManager/conf.d/wifi-power.conf > /dev/null <<EOF
[connection]
wifi.powersave = 2
EOF
check "Failed to configure WiFi power management"

log "Disabling IPv6 via NetworkManager..."
ACTIVE_CON=$(nmcli -g NAME connection show --active | head -1)
CURRENT_IPV6=$(nmcli -g ipv6.method connection show "$ACTIVE_CON")
if [ "$CURRENT_IPV6" != "ignore" ]; then
    sudo nmcli connection modify "$ACTIVE_CON" ipv6.method ignore >> "$LOGFILE" 2>&1
    check "Failed to set ipv6.method ignore"
    sudo nmcli connection down "$ACTIVE_CON" >> "$LOGFILE" 2>&1
    sudo nmcli connection up "$ACTIVE_CON" >> "$LOGFILE" 2>&1
    check "Failed to reconnect WiFi after IPv6 change"
    log "IPv6 disabled on connection: $ACTIVE_CON"
else
    log "IPv6 already disabled on connection: $ACTIVE_CON — skipping"
fi

log "Configuring avahi for IPv4 only..."
if ! grep -q "^use-ipv4=yes" /etc/avahi/avahi-daemon.conf; then
    sudo sed -i '/^use-ipv6/d' /etc/avahi/avahi-daemon.conf
    sudo sed -i '/^use-ipv4/d' /etc/avahi/avahi-daemon.conf
    sudo sed -i '/^\[server\]/a use-ipv4=yes\nuse-ipv6=no' /etc/avahi/avahi-daemon.conf
    check "Failed to configure avahi"
    log "Avahi configured for IPv4 only."
else
    log "Avahi already configured for IPv4 only — skipping"
fi
sudo systemctl enable avahi-daemon >> "$LOGFILE" 2>&1
sudo systemctl restart avahi-daemon >> "$LOGFILE" 2>&1
check "Failed to restart avahi-daemon"

log "STEP 1b complete."

# ------------------------------------------------------------------------------
# Step 1c - systemd service (replaces crontab)
# ------------------------------------------------------------------------------
log "STEP 1c: Installing Woordklok systemd service..."

sudo tee /etc/systemd/system/wk.service > /dev/null <<EOF
[Unit]
Description=Woordklok
After=network-online.target
Wants=network-online.target

[Service]
User=root
WorkingDirectory=/home/pi/ds
ExecStart=/home/pi/wk_env/bin/python /home/pi/ds/wk.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
check "Failed to create wk.service"

sudo systemctl daemon-reload >> "$LOGFILE" 2>&1
sudo systemctl enable wk >> "$LOGFILE" 2>&1
check "Failed to enable wk.service"
log "Woordklok systemd service installed and enabled."

log "Removing crontab @reboot entry if present..."
crontab -l 2>/dev/null | grep -v "@reboot.*wk.py" | crontab -
log "Crontab cleaned."

log "STEP 1c complete."
