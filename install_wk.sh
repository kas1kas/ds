#!/bin/bash
# ==============================================================================
# install_wk.sh - WordClock installation script for Raspberry Pi
# __version__ = "7.51"
# ==============================================================================

LOGFILE="/home/pi/wk_install.log"
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

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo "$msg" >&2
    echo "$msg" >> "$LOGFILE"
}

# ------------------------------------------------------------------------------
# Error handler
# ------------------------------------------------------------------------------
check() {
    if [ $? -ne 0 ]; then
        log_error "$1"
        log_error "Installation aborted. Check $LOGFILE for details."
        exit 1
    fi
}

# ==============================================================================
# Start
# ==============================================================================
echo "" >> "$LOGFILE"
log "======================================================"
log "  WordClock installation started"
log "======================================================"

# ------------------------------------------------------------------------------
# Step 1 - System packages
# ------------------------------------------------------------------------------
log "STEP 1: Installing system packages..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

log "Running apt update..."
sudo apt update -y >> "$LOGFILE" 2>&1
check "apt update failed"

log "Installing ahavi, git, python3-dev and python3-venv..."
sudo apt install -y avahi-daemon avahi-utils >> "$LOGFILE" 2>&1
sudo apt install git python3-dev python3-venv -y >> "$LOGFILE" 2>&1
check "apt install failed"

log "STEP 1 complete."
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
# Step 3 - WordClock software
# ------------------------------------------------------------------------------
log "STEP 3: Installing WordClock software..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

if [ -d "$PROJECT" ]; then
    log "Project directory $PROJECT already exists, pulling latest changes..."
    cd "$PROJECT" && git pull >> "$LOGFILE" 2>&1
    check "git pull failed"
    cd ~
else
    log "Cloning repository..."
    git clone "https://github.com/kas1kas/ds/" "$PROJECT" >> "$LOGFILE" 2>&1
    check "git clone failed"
fi

log "Creating config directory $CONFIG_DIR..."
mkdir -p "$CONFIG_DIR"
check "Failed to create $CONFIG_DIR"
chmod 755 "$CONFIG_DIR"

log "Copying config file..."
if [ -f "$CONFIG_DIR/config_loc.json" ]; then
    log "Config file already exists at $CONFIG_DIR/config_loc.json — skipping copy to preserve your settings."
elif [ -f "$PROJECT/config_loc.json" ]; then
    cp "$PROJECT/config_loc.json" "$CONFIG_DIR/config_loc.json"
    check "Failed to copy config_loc.json"
    log "Config file copied."
else
    log_error "config_loc.json not found in $PROJECT — skipping copy"
fi

log "Installing bash aliases..."
if [ -f "$PROJECT/alias.txt" ]; then
    cp "$PROJECT/alias.txt" ~/.bash_aliases
    check "Failed to copy alias.txt"
    source ~/.bash_aliases
    # Also add to .bashrc if not already there
    if ! grep -q "source ~/.bash_aliases" ~/.bashrc; then
        echo -e "\n# Load custom aliases\nif [ -f ~/.bash_aliases ]; then\n    . ~/.bash_aliases\nfi" >> ~/.bashrc
    fi
    log "Aliases loaded."
else
    log_error "alias.txt not found in $PROJECT — skipping"
fi
log "STEP 3 complete."

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

# ------------------------------------------------------------------------------
# Step 5 - Python virtual environment
# ------------------------------------------------------------------------------
log "STEP 5: Setting up Python virtual environment..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

if [ -d "$VENV" ]; then
    log "Virtual environment $VENV already exists, skipping creation."
else
    log "Creating virtual environment at $VENV..."
    python3 -m venv "$VENV"
    check "Failed to create virtual environment"
fi

log "Activating virtual environment..."
source "$VENV/bin/activate"
check "Failed to activate virtual environment"

log "Upgrading pip to latest version..."
pip install --upgrade pip >> "$LOGFILE" 2>&1
check "pip upgrade failed"

log "Installing Python packages (this may take a while)..."
pip install flask-restx rpi-ws281x python-tsl2591 buienradar --index-url https://pypi.org/simple/ >> "$LOGFILE" 2>&1
check "pip install failed — check $LOGFILE for details"

log "Deactivating virtual environment..."
deactivate

log "STEP 5 complete."

# ------------------------------------------------------------------------------
# Step 6 - First time configuration instructions
# ------------------------------------------------------------------------------
log "STEP 6: First time configuration."

CONFIG_MSG="
====================================================
  Configuration
====================================================

Before starting WordClock:
   Make sure that you know the IP address of the Wordclock, 
   so you can control it via your web browser.

   You must configure your location and hardware settings.
   Do this with:
   
   nano $CONFIG_DIR/config_loc.json
   
   -at least make sure that the GRID setting is correct
    GRID:    "11" or "16"
  
   -for all details see the file INSTALL.md
   
   A reboot is required now:
   
sudo reboot
====================================================
"
echo "$CONFIG_MSG"
echo "$CONFIG_MSG" >> "$LOGFILE"

# ------------------------------------------------------------------------------
# Done
# ------------------------------------------------------------------------------
log "======================================================"
log "  WordClock installation finished successfully!"
log "  Log saved to: $LOGFILE"
log "======================================================"
