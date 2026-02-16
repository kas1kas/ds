#!/bin/bash

# WordClock Installation Script
# This script installs/updates the WordClock application while preserving user configs

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/kas1kas/ds.git"
INSTALL_DIR="/home/pi/ds"
USER_CONFIG_DIR="/home/pi/.wordclock"
BACKUP_DIR="/home/pi/.wordclock_backup"
LOG_FILE="/home/pi/wordclock_install.log"

# Logging function
log() {
    echo -e "${2:-$BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1" "$RED" >&2
    exit 1
}

# Check if running as root (not recommended for Pi user)
if [ "$EUID" -eq 0 ]; then
    error_exit "Please do not run as root. Run as the 'pi' user."
fi

# Create log file
touch "$LOG_FILE"
log "=== WordClock Installation/Update Started ===" "$GREEN"

# Step 1: Check for git
log "Checking for git..."
if ! command -v git &> /dev/null; then
    log "Git not found. Installing git..." "$YELLOW"
    sudo apt-get update && sudo apt-get install -y git || error_exit "Failed to install git"
fi

# Step 2: Clone or update repository
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Existing installation found. Updating from GitHub..." "$YELLOW"

    # Backup user configs before update (just in case)
    log "Creating backup of user configs..."
    mkdir -p "$BACKUP_DIR"
    if [ -f "$USER_CONFIG_DIR/config_loc.json" ]; then
        cp "$USER_CONFIG_DIR/config_loc.json" "$BACKUP_DIR/" 2>/dev/null || log "No config_loc.json to backup" "$YELLOW"
    fi
    if [ -f "$USER_CONFIG_DIR/config_gen.json" ]; then
        cp "$USER_CONFIG_DIR/config_gen.json" "$BACKUP_DIR/" 2>/dev/null || log "No config_gen.json to backup" "$YELLOW"
    fi

    # Update repository
    cd "$INSTALL_DIR"
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)

    if [ "$LOCAL" != "$REMOTE" ]; then
        log "Updates available. Pulling changes..."
        git pull origin main || error_exit "Failed to pull updates"
        log "Repository updated successfully" "$GREEN"
    else
        log "Already up to date" "$GREEN"
    fi
else
    log "First time installation. Cloning repository..." "$YELLOW"
    git clone "$REPO_URL" "$INSTALL_DIR" || error_exit "Failed to clone repository"
    log "Repository cloned successfully" "$GREEN"
fi

# Step 3: Create user config directory
log "Setting up user config directory..."
mkdir -p "$USER_CONFIG_DIR"
chmod 755 "$USER_CONFIG_DIR"
log "User config directory: $USER_CONFIG_DIR"

# Step 4: Check for default configs
log "Checking for default config templates..."
if [ ! -d "$INSTALL_DIR/default_configs" ]; then
    error_exit "default_configs directory not found in repository"
fi

# Step 5: Copy/update config files (without overwriting user modifications)
log "Setting up configuration files..." "$YELLOW"

# Function to copy config if it doesn't exist or if forced
copy_config() {
    local src="$1"
    local dst="$2"
    local name="$3"

    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        chmod 644 "$dst"
        log "  Created $name" "$GREEN"
    else
        log "  $name already exists - keeping user version" "$GREEN"

        # Optional: Show differences if user wants to see updates
        if [ "$1" = "--show-diff" ]; then
            if ! cmp -s "$src" "$dst"; then
                log "  Note: Template has changes. Compare with: diff $src $dst" "$YELLOW"
            fi
        fi
    fi
}

# Copy config files (don't overwrite existing user configs)
copy_config "$INSTALL_DIR/default_configs/config_gen.json" "$USER_CONFIG_DIR/config_gen.json" "General config (config_gen.json)"
copy_config "$INSTALL_DIR/default_configs/config_loc.json" "$USER_CONFIG_DIR/config_loc.json" "Local config (config_loc.json)"

# Step 6: Check for Python dependencies
log "Checking Python dependencies..."
if command -v pip3 &> /dev/null; then
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        log "Installing Python packages from requirements.txt..." "$YELLOW"
        pip3 install --user -r "$INSTALL_DIR/requirements.txt" || log "Warning: Some packages may not have installed" "$YELLOW"
    else
        # Install common dependencies
        log "Installing common Python packages..." "$YELLOW"
        pip3 install --user RPi.GPIO || log "Warning: RPi.GPIO installation failed" "$YELLOW"
    fi
else
    log "pip3 not found. Installing python3-pip..." "$YELLOW"
    sudo apt-get install -y python3-pip || log "Warning: Could not install pip3" "$YELLOW"
fi

# Step 7: Set up proper permissions
log "Setting file permissions..."
chmod +x "$INSTALL_DIR/wk.py" 2>/dev/null || log "wk.py not found or not executable" "$YELLOW"
chmod -R 755 "$INSTALL_DIR"

# Step 8: Create a version file
log "Recording installation version..."
echo "INSTALL_DATE=$(date '+%Y-%m-%d %H:%M:%S')" > "$INSTALL_DIR/.version"
echo "GIT_COMMIT=$(cd $INSTALL_DIR && git rev-parse HEAD)" >> "$INSTALL_DIR/.version"
echo "GIT_BRANCH=$(cd $INSTALL_DIR && git rev-parse --abbrev-ref HEAD)" >> "$INSTALL_DIR/.version"

# Step 9: Test configuration
log "Testing configuration..."
if [ -f "$INSTALL_DIR/wk.py" ]; then
    log "Running config test..." "$YELLOW"
    cd "$INSTALL_DIR"
    python3 -c "
import json
import os

try:
    with open('$USER_CONFIG_DIR/config_gen.json') as f:
        config_gen = json.load(f)
    with open('$USER_CONFIG_DIR/config_loc.json') as f:
        config_loc = json.load(f)
    merged = {**config_gen, **config_loc}
    print('✓ Configuration files are valid JSON')
    print('✓ Config loaded successfully')
except Exception as e:
    print('✗ Config error: ' + str(e))
    exit(1)
" 2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "Configuration test PASSED" "$GREEN"
    else
        log "Configuration test FAILED - please check your config files" "$RED"
    fi
fi

# Step 10: Create a symlink for easy execution (optional)
if [ ! -f "/home/pi/bin/wordclock" ]; then
    mkdir -p /home/pi/bin
    ln -s "$INSTALL_DIR/wk.py" /home/pi/bin/wordclock 2>/dev/null || log "Could not create symlink" "$YELLOW"
    log "Created 'wordclock' command in ~/bin/" "$GREEN"
fi

# Step 11: Cleanup old backups
log "Cleaning up old backups..."
rm -rf "$BACKUP_DIR"

# Final message
log ""
log "=== Installation Complete! ===" "$GREEN"
log ""
log "📁 Installation directory: $INSTALL_DIR"
log "⚙️  User config directory: $USER_CONFIG_DIR"
log "📝 Log file: $LOG_FILE"
log ""
log "To run WordClock:" "$BLUE"
log "  cd $INSTALL_DIR && python3 wk.py" "$BLUE"
log "  or if symlink created: wordclock" "$BLUE"
log ""
log "To update in the future:" "$BLUE"
log "  cd $INSTALL_DIR && git pull" "$BLUE"
log "  # Your configs in ~/.wordclock/ will be preserved" "$BLUE"
log ""

# Check for any errors in log
if grep -i "error\|warning" "$LOG_FILE" > /dev/null; then
    log "Note: Some warnings/errors occurred. Check $LOG_FILE for details." "$YELLOW"
fi
