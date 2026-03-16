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
# Step 2 - WordClock software
# ------------------------------------------------------------------------------
log "STEP 2: Installing WordClock software..."

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

log "Setting up crontab..."
CRONTAB_INSTALLED=false
if [ -f "$PROJECT/crontab.txt" ]; then
    # Strip Windows line endings just in case
    sed -i 's/\r//' "$PROJECT/crontab.txt"
    if crontab "$PROJECT/crontab.txt" >> "$LOGFILE" 2>&1; then
        log "Crontab installed from $PROJECT/crontab.txt"
        CRONTAB_INSTALLED=true
    else
        log_error "Failed to install crontab from $PROJECT/crontab.txt — trying fallback"
    fi
fi
if [ "$CRONTAB_INSTALLED" = false ]; then
    log "Installing fallback crontab entry..."
    echo "@reboot sudo $VENV/bin/python $PROJECT/wk.py > /home/pi/cron_log.txt 2>&1" | crontab -
    if [ $? -eq 0 ]; then
        log "Fallback crontab installed successfully."
    else
        log_error "Failed to install fallback crontab — please set it up manually."
    fi
fi

log "STEP 2 complete."

# ------------------------------------------------------------------------------
# Step 3 - Python virtual environment
# ------------------------------------------------------------------------------
log "STEP 3: Setting up Python virtual environment..."

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

log "STEP 3 complete."

# ------------------------------------------------------------------------------
# Step 4 & 5 - First time configuration instructions
# ------------------------------------------------------------------------------
log "STEP 4: First time configuration."

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

The wordclock starts automatically after a reboot.

After configuring, start WordClock with:
  swk

Or manually:
  sudo $VENV/bin/python $PROJECT/wk.py

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
