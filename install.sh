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
REPO_URL="https://github.com/here_my_projectname/ds.git"
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
    REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)
    
    if [ "$LOCAL" != "$REMOTE" ]; then
        log "Updates available. Pulling changes..."
        git pull origin main || git pull origin master || error_exit "Failed to pull updates"
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

# Step 4: Copy config files to user directory (without overwriting user modifications)
log "Setting up configuration files..." "$YELLOW"

# Function to copy config if it doesn't exist
copy_config() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ ! -f "$dst" ]; then
        if [ -f "$src" ]; then
            cp "$src" "$dst"
            chmod 644 "$dst"
            log "  ✅ Created $name from repository" "$GREEN"
        else
            log "  ⚠️  Warning: $src not found in repository" "$YELLOW"
        fi
    else
        log "  ✅ $name already exists - keeping user version" "$GREEN"
        
        # Optional: Show if repository version is different
        if [ -f "$src" ]; then
            if ! cmp -s "$src" "$dst"; then
                log "  📝 Note: Repository template differs from your config. Compare with: diff $src $dst" "$YELLOW"
            fi
        fi
    fi
}

# Copy config files from the main directory
log "Looking for config files in $INSTALL_DIR..."
copy_config "$INSTALL_DIR/config_gen.json" "$USER_CONFIG_DIR/config_gen.json" "General config (config_gen.json)"
copy_config "$INSTALL_DIR/config_loc.json" "$USER_CONFIG_DIR/config_loc.json" "Local config (config_loc.json)"

# Step 5: Create a README in the user config directory
if [ ! -f "$USER_CONFIG_DIR/README.txt" ]; then
    cat > "$USER_CONFIG_DIR/README.txt" << EOF
WordClock User Configuration Directory
======================================
This directory contains your personal WordClock configuration files.

- config_gen.json: General settings (can be updated from repository)
- config_loc.json: Local/User settings (preserved during updates)

These files are NEVER overwritten during updates.
If you want to reset to defaults, delete the file and run the install script again.

To compare your config with the latest repository version:
  diff ~/.wordclock/config_gen.json ~/ds/config_gen.json
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
    else
        # Check for common dependencies
        log "No requirements.txt found. Checking for common packages..." "$YELLOW"
        pip3 list | grep -E "RPi.GPIO|pillow|numpy" || log "Some common packages may be missing" "$YELLOW"
    fi
else
    log "pip3 not found. Installing python3-pip..." "$YELLOW"
    sudo apt-get install -y python3-pip || log "⚠️  Warning: Could not install pip3" "$YELLOW"
fi

# Step 7: Set up proper permissions
log "Setting file permissions..."
chmod +x "$INSTALL_DIR/wk.py" 2>/dev/null || log "⚠️  wk.py not found or not executable" "$YELLOW"
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
    # Check if user configs exist
    gen_path = '$USER_CONFIG_DIR/config_gen.json'
    loc_path = '$USER_CONFIG_DIR/config_loc.json'
    
    if not os.path.exists(gen_path):
        print('⚠️  Warning: config_gen.json not found in user directory')
        sys.exit(1)
    
    if not os.path.exists(loc_path):
        print('⚠️  Warning: config_loc.json not found in user directory')
        sys.exit(1)
    
    # Try loading both configs
    with open(gen_path) as f:
        config_gen = json.load(f)
    with open(loc_path) as f:
        config_loc = json.load(f)
    
    # Test merge
    merged = {**config_gen, **config_loc}
    
    # Check for VERSION key (common required key)
    if 'VERSION' not in merged:
        print('⚠️  Warning: VERSION key not found in config')
    else:
        print('✅ Configuration files are valid JSON')
        print('✅ Config loaded successfully')
        print(f'✅ Config version: {merged.get(\"VERSION\", \"unknown\")}')
        
except json.JSONDecodeError as e:
    print(f'❌ Invalid JSON: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Config error: {e}')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✅ Configuration test PASSED" "$GREEN"
    else
        log "⚠️  Configuration test had warnings - please check your config files" "$YELLOW"
    fi
fi

# Step 10: Cleanup old backups
log "Cleaning up old backups..."
rm -rf "$BACKUP_DIR"

# Step 11: Show what files were copied
log "Checking config files in user directory..."
if [ -f "$USER_CONFIG_DIR/config_gen.json" ]; then
    log "  ✅ config_gen.json exists in user directory" "$GREEN"
else
    log "  ⚠️  config_gen.json not found in user directory" "$YELLOW"
fi

if [ -f "$USER_CONFIG_DIR/config_loc.json" ]; then
    log "  ✅ config_loc.json exists in user directory" "$GREEN"
else
    log "  ⚠️  config_loc.json not found in user directory" "$YELLOW"
fi

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
log ""
log "To update in the future:" "$BLUE"
log "  cd $INSTALL_DIR && git pull" "$BLUE"
log "  # Your configs in ~/.wordclock/ are preserved" "$GREEN"
log ""
log "Your config files are now in ~/.wordclock/ :" "$BLUE"
if [ -d "$USER_CONFIG_DIR" ]; then
    ls -la "$USER_CONFIG_DIR/" | grep -v "README" | sed 's/^/  /' || echo "  (No config files yet)"
fi
log ""

# Check for any errors in log
if grep -i "error\|warning" "$LOG_FILE" > /dev/null; then
    log "Note: Some warnings/errors occurred. Check $LOG_FILE for details." "$YELLOW"
fi
