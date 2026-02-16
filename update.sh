#!/bin/bash

# Quick update script
INSTALL_DIR="/home/pi/ds"
USER_CONFIG_DIR="/home/pi/.wordclock"

echo "Updating WordClock from GitHub..."
cd "$INSTALL_DIR"

# Stash any local changes (like config files that shouldn't be there)
git stash

# Pull updates
git pull

# Restore stashed changes (if any)
git stash pop

echo "Update complete! Your configs in $USER_CONFIG_DIR are untouched."
echo "If there are new config options, check the templates in $INSTALL_DIR/default_configs/"
