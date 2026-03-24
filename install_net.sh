#!/bin/bash
# ==============================================================================
# install_net.sh - network update installation script for Raspberry Pi
#                  create woordklok as service
# __version__ = "7.51"
# ==============================================================================

LOGFILE="/home/pi/wk_net_install.log"
VENV="/home/pi/wk_env"
PROJECT="/home/pi/ds"
CONFIG_DIR="/home/pi/.wordclock"

# ------------------------------------------------------------------------------
# Logging helper
# ------------------------------------------------------------------------------
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOGFILE"
}
# ------------------------------------------------------------------------------
# Step 2 - Network configuration (IPv6, WiFi power management)
# ------------------------------------------------------------------------------
log "STEP 2: Configuring network (IPv6, WiFi power management)..."

log "For zero2W driver bug: Checking for brcmfmac WiFi driver fix..."

WIFI_DRIVER=$(nmcli -g GENERAL.DRIVER device show wlan0 2>/dev/null)
PI_MODEL=$(cat /proc/cpuinfo | grep Model | head -1)

log "WiFi driver: $WIFI_DRIVER"
log "Pi model: $PI_MODEL"

if lsmod | grep -q "brcmfmac"; then
    log "brcmfmac driver detected — applying fix..."

    if ! grep -q "roamoff" /etc/modprobe.d/brcmfmac.conf 2>/dev/null; then
        sudo tee /etc/modprobe.d/brcmfmac.conf > /dev/null <<EOF
options brcmfmac roamoff=1 feature_disable=0x82000
EOF
        check "Failed to create brcmfmac.conf"

        sudo tee /etc/NetworkManager/conf.d/wifi-power.conf > /dev/null <<EOF
[connection]
wifi.powersave = 2
EOF
        check "Failed to configure WiFi power management"
        log "brcmfmac driver fix and power management applied."
    else
        log "brcmfmac fix already present — skipping"
    fi
else
    log "brcmfmac driver not detected ($(lsmod | grep wifi || echo 'other driver')) — skipping fix"
fi

log "zero2W STEP complete."

log "Disabling IPv6 via sysctl..."

# Define the configuration file path
SYSCTL_CONF="/etc/sysctl.d/99-disable-ipv6.conf"

# Create or overwrite the configuration file with the required settings
# Using 'cat' with a here-document ensures the file content is exactly as specified
sudo bash -c "cat > $SYSCTL_CONF <<EOF
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF" >> "$LOGFILE" 2>&1
check "Failed to create or write to $SYSCTL_CONF"

log "Configuration written to $SYSCTL_CONF, applying settings..."

# Apply the settings immediately
sudo sysctl -p "$SYSCTL_CONF" >> "$LOGFILE" 2>&1
check "Failed to apply sysctl settings from $SYSCTL_CONF"

log "IPv6 disabled globally via sysctl."

log "STEP 2 complete."

# ------------------------------------------------------------------------------
# Step 4 - systemd service (replaces crontab)
# ------------------------------------------------------------------------------
log "STEP 4: Installing Woordklok systemd service..."

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

log "STEP 4 complete."

