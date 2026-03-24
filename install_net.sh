#!/bin/bash
# ==============================================================================
# install_net.sh - network update installation script for Raspberry Pi
# __version__ = "7.45"
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
# Step 1b - Network configuration (IPv6, WiFi power management)
# ------------------------------------------------------------------------------
log "STEP 1b: Configuring network (IPv6, WiFi power management)..."


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

# ------------------------------------------------------------------------------
# Step 1d - Fix brcmfmac WiFi driver bug (Pi Zero 2W only)
# ------------------------------------------------------------------------------
log "STEP 1d: Checking for brcmfmac WiFi driver fix..."

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

log "STEP 1d complete."
