#!/bin/bash
# ==============================================================================
# install_wk.sh - WordClock installation script for Raspberry Pi
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

log "Configuring mDNS and disabling IPv6"
# Disable IPv6 at kernel level
if ! grep -q "disable_ipv6" /etc/sysctl.conf; then
    echo "net.ipv6.conf.all.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv6.conf.default.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
fi
sudo sysctl -p

# Configure avahi to use IPv4 only (idempotent)
sudo sed -i '/^use-ipv6/d' /etc/avahi/avahi-daemon.conf
sudo sed -i '/^use-ipv4/d' /etc/avahi/avahi-daemon.conf
sudo sed -i '/^\[server\]/a use-ipv4=yes\nuse-ipv6=no' /etc/avahi/avahi-daemon.conf
sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon

log "STEP 1 complete."
# ------------------------------------------------------------------------------
# Step 2 - Network configuration (mDNS, IPv6, WiFi power management)
# ------------------------------------------------------------------------------
log "STEP 2: Configuring network (mDNS, IPv6, WiFi power management)..."

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
  First time configuration
====================================================

Before starting WordClock, 
   Make sure that you know the IP address of the Wordclock, 
   so you can control it via your web browser.

   You need to configure your location and hardware settings.
   The config file is located at:
   $CONFIG_DIR/config_loc.json

   Open it with:
   nano $CONFIG_DIR/config_loc.json

  Key settings to check/update:
   -see the file INSTALL.md
   -at least make sure that the GRID setting is correct

  GRID:        "11" or "16"
====================================================
"
echo ""
echo "=== Install complete! ==="
echo "=== mDNS ready after reboot: $(hostname).local ==="
echo ""
echo "A reboot is required to apply all changes."
echo "Run: sudo reboot"
echo "$CONFIG_MSG"
echo "$CONFIG_MSG" >> "$LOGFILE"

# ------------------------------------------------------------------------------
# Done
# ------------------------------------------------------------------------------
log "======================================================"
log "  WordClock installation finished successfully!"
log "  Log saved to: $LOGFILE"
log "======================================================"
