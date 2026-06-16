#!/bin/bash
# ==============================================================================
# install_wk.sh - WordClock installation script for Raspberry Pi
# __version__ = "8.30"
# ==============================================================================

LOGFILE="/home/pi/wk_install.log"
VENV="/home/pi/wk_env"
PROJECT="/home/pi/ds"
BRANCH="unify"
CONFIG_DIR="/home/pi/.wordclock"
CONFIG_LOC="$CONFIG_DIR/config_loc.toml"

# ------------------------------------------------------------------------------
# Logging helpers
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
log "  $(date '+%A %d %B %Y  %H:%M:%S')"
log "======================================================"

# ------------------------------------------------------------------------------
# Step 1 - System packages
# ------------------------------------------------------------------------------
log "STEP 1: Installing system packages..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

log "Running apt update..."
sudo apt update -y >> "$LOGFILE" 2>&1
check "apt update failed"

log "Installing avahi, git, python3-dev, python3-venv, i2c-tools..."
sudo apt install -y avahi-daemon avahi-utils >> "$LOGFILE" 2>&1
sudo apt install -y git python3-dev python3-venv i2c-tools >> "$LOGFILE" 2>&1
check "apt install failed"

log "STEP 1 complete."

# ------------------------------------------------------------------------------
# Step 2 - Network configuration (IPv6, WiFi power management)
# ------------------------------------------------------------------------------
log "STEP 2: Configuring network..."

PI_MODEL=$(grep Model /proc/cpuinfo | head -1)
log "Pi model: $PI_MODEL"

log "Checking for brcmfmac WiFi driver fix (Zero 2W)..."
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
        log "brcmfmac fix and WiFi power management applied."
    else
        log "brcmfmac fix already present — skipping."
    fi
else
    log "brcmfmac driver not detected — skipping fix."
fi

log "Disabling IPv6..."
SYSCTL_CONF="/etc/sysctl.d/99-disable-ipv6.conf"
sudo bash -c "cat > $SYSCTL_CONF <<EOF
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF" >> "$LOGFILE" 2>&1
check "Failed to write $SYSCTL_CONF"
sudo sysctl -p "$SYSCTL_CONF" >> "$LOGFILE" 2>&1
check "Failed to apply sysctl settings"
log "IPv6 disabled."

log "STEP 2 complete."

# ------------------------------------------------------------------------------
# Step 2b - Enable I2C
# ------------------------------------------------------------------------------
log "STEP 2b: Enabling I2C interface..."

if sudo raspi-config nonint do_i2c 0 >> "$LOGFILE" 2>&1; then
    log "I2C enabled via raspi-config."
else
    log_error "raspi-config do_i2c failed — trying direct config.txt edit..."
    BOOT_CONFIG="/boot/firmware/config.txt"
    [ ! -f "$BOOT_CONFIG" ] && BOOT_CONFIG="/boot/config.txt"
    if ! grep -q "^dtparam=i2c_arm=on" "$BOOT_CONFIG"; then
        echo "dtparam=i2c_arm=on" | sudo tee -a "$BOOT_CONFIG" >> "$LOGFILE" 2>&1
        check "Failed to enable I2C in $BOOT_CONFIG"
        log "I2C enabled via $BOOT_CONFIG."
    else
        log "I2C already enabled in $BOOT_CONFIG."
    fi
fi

if ! lsmod | grep -q "i2c_dev"; then
    sudo modprobe i2c-dev >> "$LOGFILE" 2>&1
    check "Failed to load i2c-dev kernel module"
    log "i2c-dev kernel module loaded."
else
    log "i2c-dev already loaded."
fi

log "STEP 2b complete."

# ------------------------------------------------------------------------------
# Step 3 - WordClock software
# ------------------------------------------------------------------------------
log "STEP 3: Installing WordClock software (branch: $BRANCH)..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

if [ -d "$PROJECT" ]; then
    log "Project directory $PROJECT exists — pulling latest changes..."
    cd "$PROJECT"
    git fetch origin >> "$LOGFILE" 2>&1
    check "git fetch failed"
    git checkout "$BRANCH" >> "$LOGFILE" 2>&1
    check "git checkout $BRANCH failed"
    git pull origin "$BRANCH" >> "$LOGFILE" 2>&1
    check "git pull failed"
    cd ~
else
    log "Cloning repository (branch: $BRANCH)..."
    git clone --branch "$BRANCH" "https://github.com/kas1kas/ds/" "$PROJECT" >> "$LOGFILE" 2>&1
    check "git clone failed"
fi

log "Creating config directory $CONFIG_DIR..."
mkdir -p "$CONFIG_DIR"
check "Failed to create $CONFIG_DIR"
chmod 755 "$CONFIG_DIR"

# Copy config_loc.toml only on first install — never overwrite user settings.
# On upgrade: if old config_loc.json exists and no toml yet, run migration.
if [ -f "$CONFIG_LOC" ]; then
    log "Config file already exists at $CONFIG_LOC — preserving user settings."
elif [ -f "$CONFIG_DIR/config_loc.json" ]; then
    log "Found old config_loc.json — running migration to TOML..."
    source "$VENV/bin/activate" 2>/dev/null
    python3 "$PROJECT/migrate_config.py" \
        --json "$CONFIG_DIR/config_loc.json" \
        --toml "$CONFIG_LOC" \
        --template "$PROJECT/config_loc.toml" >> "$LOGFILE" 2>&1
    if [ $? -eq 0 ]; then
        log "Migration successful. Review $CONFIG_LOC before restarting."
    else
        log_error "Migration failed — copying template instead."
        cp "$PROJECT/config_loc.toml" "$CONFIG_LOC"
        check "Failed to copy config_loc.toml"
        log "Template config copied to $CONFIG_LOC — please edit before starting."
    fi
elif [ -f "$PROJECT/config_loc.toml" ]; then
    cp "$PROJECT/config_loc.toml" "$CONFIG_LOC"
    check "Failed to copy config_loc.toml"
    log "Config template copied to $CONFIG_LOC."
else
    log_error "config_loc.toml not found in $PROJECT — skipping copy."
fi

log "Installing bash aliases..."
if [ -f "$PROJECT/alias.txt" ]; then
    cp "$PROJECT/alias.txt" ~/.bash_aliases
    check "Failed to copy alias.txt"
    source ~/.bash_aliases
    if ! grep -q "source ~/.bash_aliases" ~/.bashrc; then
        echo -e "\n# Load custom aliases\nif [ -f ~/.bash_aliases ]; then\n    . ~/.bash_aliases\nfi" >> ~/.bashrc
    fi
    log "Aliases installed."
else
    log "alias.txt not found in $PROJECT — skipping."
fi

log "STEP 3 complete."

# ------------------------------------------------------------------------------
# Step 4 - WordClock systemd service
# ------------------------------------------------------------------------------
log "STEP 4: Installing Woordklok systemd service..."

sudo tee /etc/systemd/system/wk.service > /dev/null <<EOF
[Unit]
Description=Woordklok
After=network-online.target lux_daemon.service
Wants=network-online.target lux_daemon.service

[Service]
User=root
WorkingDirectory=/home/pi/ds
ExecStart=/home/pi/wk_env/bin/python /home/pi/ds/wk.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
check "Failed to create wk.service"

sudo systemctl daemon-reload >> "$LOGFILE" 2>&1
sudo systemctl enable wk >> "$LOGFILE" 2>&1
check "Failed to enable wk.service"
log "wk.service installed and enabled."

log "Removing crontab @reboot entry if present..."
crontab -l 2>/dev/null | grep -v "@reboot.*wk.py" | crontab -
log "Crontab cleaned."

log "STEP 4 complete."

# ------------------------------------------------------------------------------
# Step 4b - lux_daemon systemd service
# Reads SENSOR from config_loc.toml so it works for all hardware configs.
# Falls back to "none" if the config file or key is missing.
# ------------------------------------------------------------------------------
log "STEP 4b: Installing lux_daemon systemd service..."

# Read sensor type from config_loc.toml
if [ -f "$CONFIG_LOC" ]; then
    SENSOR=$(grep -E '^\s*sensor\s*=' "$CONFIG_LOC" \
             | head -1 \
             | sed 's/.*=\s*//;s/[" ]//g')
    log "Sensor type from config: '$SENSOR'"
else
    SENSOR="none"
    log "Config not found — defaulting sensor to 'none'."
fi

# Normalise to lowercase for comparison
SENSOR_LC=$(echo "$SENSOR" | tr '[:upper:]' '[:lower:]')

if [ "$SENSOR_LC" = "none" ] || [ -z "$SENSOR_LC" ]; then
    log "Sensor disabled (sensor=none) — lux_daemon will not be started."
    # Install a no-op service so wk.service dependency doesn't block boot
    sudo tee /etc/systemd/system/lux_daemon.service > /dev/null <<EOF
[Unit]
Description=Light sensor lux daemon (disabled — sensor=none)
Before=wk.service

[Service]
Type=oneshot
ExecStart=/bin/true

[Install]
WantedBy=multi-user.target
EOF
else
    log "Installing lux_daemon for sensor: $SENSOR"
    sudo tee /etc/systemd/system/lux_daemon.service > /dev/null <<EOF
[Unit]
Description=Light sensor lux daemon (Unix socket)
Before=wk.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ds
ExecStart=/home/pi/wk_env/bin/python3 /home/pi/ds/lux_daemon.py --sensor ${SENSOR}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
fi

check "Failed to create lux_daemon.service"
sudo systemctl daemon-reload >> "$LOGFILE" 2>&1
sudo systemctl enable lux_daemon >> "$LOGFILE" 2>&1
check "Failed to enable lux_daemon.service"
log "lux_daemon.service installed and enabled."

log "STEP 4b complete."

# ------------------------------------------------------------------------------
# Step 5 - Python virtual environment
# ------------------------------------------------------------------------------
log "STEP 5: Setting up Python virtual environment..."

cd ~ || { log_error "Cannot cd to home directory"; exit 1; }

if [ -d "$VENV" ]; then
    log "Virtual environment $VENV already exists — skipping creation."
else
    log "Creating virtual environment at $VENV..."
    python3 -m venv "$VENV"
    check "Failed to create virtual environment"
fi

log "Activating virtual environment..."
source "$VENV/bin/activate"
check "Failed to activate virtual environment"

log "Upgrading pip..."
pip install --upgrade pip >> "$LOGFILE" 2>&1
check "pip upgrade failed"

log "Installing Python packages..."
pip install flask rpi-ws281x smbus2 requests \
    --index-url https://pypi.org/simple/ >> "$LOGFILE" 2>&1
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

Before starting WordClock, review your settings:

   nano $CONFIG_LOC

   Uncomment the correct hardware, language, sensor,
   and effect lines for your clock.

   For full details see INSTALL.md in $PROJECT.

   A reboot is required to start the services:

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
