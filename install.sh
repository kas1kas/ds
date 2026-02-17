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
    
    # Backup user config before update (just in case)
    if [ -f "$USER_CONFIG_DIR/config_loc.json" ]; then
        log "Creating backup of user config..."
        mkdir -p "$BACKUP_DIR"
        cp "$USER_CONFIG_DIR/config_loc.json" "$BACKUP_DIR/" 
        log "Backup created at $BACKUP_DIR/config_loc.json" "$GREEN"
    fi
    
    # Update repository - this will update config_gen.json automatically!
    cd "$INSTALL_DIR"
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)
    
    if [ "$LOCAL" != "$REMOTE" ]; then
        log "Updates available. Pulling changes..."
        git pull origin main || git pull origin master || error_exit "Failed to pull updates"
        log "Repository updated successfully" "$GREEN"
        log "Note: config_gen.json has been updated with latest changes" "$YELLOW"
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

# Step 4: ONLY copy config_loc.json to user directory (config_gen.json stays in repo!)
log "Setting up user configuration file..." "$YELLOW"

# Function to copy config if it doesn't exist
copy_user_config() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ ! -f "$dst" ]; then
        if [ -f "$src" ]; then
            cp "$src" "$dst"
            chmod 644 "$dst"
            log "  ✅ Created $name from repository" "$GREEN"
            log "  📝 EDIT THIS FILE: $dst" "$YELLOW"
        else
            log "  ⚠️  Warning: $src not found in repository" "$YELLOW"
        fi
    else
        log "  ✅ $name already exists - keeping your custom settings" "$GREEN"
        log "  📝 Your config: $dst" "$BLUE"
        
        # Show if repository version is different (for information only)
        if [ -f "$src" ]; then
            if ! cmp -s "$src" "$dst"; then
                log "  📝 Note: New template available. Compare with: diff $src $dst" "$YELLOW"
            fi
        fi
    fi
}

# ONLY copy config_loc.json - this is the user's personal config
copy_user_config "$INSTALL_DIR/config_loc.json" "$USER_CONFIG_DIR/config_loc.json" "Personal config (config_loc.json)"

# config_gen.json stays in the repository and will be updated with git pull!
log "  ℹ️  System config (config_gen.json) remains in $INSTALL_DIR and will update with git" "$BLUE"

# Step 5: Create a README in the user config directory
if [ ! -f "$USER_CONFIG_DIR/README.txt" ]; then
    cat > "$USER_CONFIG_DIR/README.txt" << EOF
WordClock User Configuration
============================

This directory contains your PERSONAL WordClock configuration.

FILES:
------
config_loc.json  - YOUR personal settings (edit this one!)
                  This file will NOT be overwritten during updates.

IMPORTANT:
----------
- System settings (config_gen.json) are in: /home/pi/ds/config_gen.json
- That file updates automatically when you run 'git pull'
- Your personal settings here will be preserved.

TO EDIT YOUR SETTINGS:
---------------------
nano ~/.wordclock/config_loc.json

TO COMPARE WITH LATEST TEMPLATE:
------------------------------
diff ~/.wordclock/config_loc.json ~/ds/config_loc.json

EOF
    log "  ✅ Created README in user config directory" "$GREEN"
fi

# Step 6: Check for Python dependencies
log "Checking Python dependencies..."
if command -v pip3 &> /dev/null; then
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        log "Installing Python packages from requirements.txt..." "$YELLOW"
        pip3 install --user -r "$INSTALL_DIR/requirements.txt" || log "⚠️  Warning: Some packages may not have installed" "$YELLOW"
    fi
else
    log "pip3 not found. Installing python3-pip..." "$YELLOW"
    sudo apt-get install -y python3-pip || log "⚠️  Warning: Could not install pip3" "$YELLOW"
fi

# Step 7: Set up proper permissions
log "Setting file permissions..."
chmod +x "$INSTALL_DIR/wk.py" 2>/dev/null || log "⚠️  wk.py not found" "$YELLOW"
chmod -R 755 "$INSTALL_DIR"

# Step 8: Create a version file
log "Recording installation version..."
{
    echo "INSTALL_DATE=$(date '+%Y-%m-%d %H:%M:%S')"
    echo "GIT_COMMIT=$(cd $INSTALL_DIR && git rev-parse HEAD)"
    echo "GIT_BRANCH=$(cd $INSTALL_DIR && git rev-parse --abbrev-ref HEAD)"
} > "$INSTALL_DIR/.version"

# Step 9: Test configuration
log "Testing configuration..."
if [ -f "$INSTALL_DIR/wk.py" ]; then
    log "Running config test..." "$YELLOW"
    cd "$INSTALL_DIR"
    python3 -c "
import json
import os
import sys

try:
    # Load system config from repository (this updates with git)
    system_config_path = '$INSTALL_DIR/config_gen.json'
    if not os.path.exists(system_config_path):
        print(f'❌ System config not found: {system_config_path}')
        sys.exit(1)
    
    with open(system_config_path) as f:
        system_config = json.load(f)
    print('✅ System config loaded from repository')
    
    # Load user config from hidden folder (preserved)
    user_config_path = '$USER_CONFIG_DIR/config_loc.json'
    if os.path.exists(user_config_path):
        with open(user_config_path) as f:
            user_config = json.load(f)
        print('✅ User config loaded from ~/.wordclock/')
    else:
        user_config = {}
        print('⚠️  No user config found - using defaults only')
    
    # Test merge
    merged = {**system_config, **user_config}
    
    if 'VERSION' in merged:
        print(f'✅ Configuration valid (version: {merged[\"VERSION\"]})')
    else:
        print('⚠️  Warning: VERSION key not found in config')
        
except json.JSONDecodeError as e:
    print(f'❌ Invalid JSON: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Config error: {e}')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"
fi

# Step 10: Cleanup old backups
log "Cleaning up old backups..."
rm -rf "$BACKUP_DIR"

# Step 11: Summary
log ""
log "=== Installation Complete! ===" "$GREEN"
log ""
log "📁 System files (updated by git): $INSTALL_DIR"
log "   - config_gen.json (updates automatically)" "$BLUE"
log ""
log "⚙️  Your personal config (NOT overwritten): $USER_CONFIG_DIR/config_loc.json" "$GREEN"
log ""
log "📝 To edit your personal settings:" "$YELLOW"
log "   nano ~/.wordclock/config_loc.json" "$BLUE"
log ""
log "🔄 To update system files (including config_gen.json):" "$YELLOW"
log "   ~/ds/update.sh" "$BLUE"
log ""

# Check for any errors in log
if grep -i "error\|warning" "$LOG_FILE" > /dev/null; then
    log "Note: Some warnings/errors occurred. Check $LOG_FILE for details." "$YELLOW"
fi
