#!/bin/bash
# update.sh - Safe update script for WordClock

INSTALL_DIR="/home/pi/ds"
USER_CONFIG_DIR="/home/pi/.wordclock"

echo "🔄 Updating WordClock..."
echo "========================"

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Installation not found at $INSTALL_DIR"
    echo "Please run install.sh first"
    exit 1
fi

cd "$INSTALL_DIR"

# Check for git repository
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository"
    exit 1
fi

# Save current version for comparison
CURRENT_VERSION=$(git rev-parse HEAD)

# Pull updates with fast-forward only
echo "📥 Fetching updates from GitHub..."
git fetch origin

# Check if there are updates
REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

if [ "$CURRENT_VERSION" = "$REMOTE" ]; then
    echo "✅ Already up to date!"
    exit 0
fi

# Try to pull with fast-forward only
echo "📦 Applying updates..."
if git pull --ff-only origin main 2>/dev/null || git pull --ff-only origin master 2>/dev/null; then
    echo "✅ Update successful!"
    
    # Show what changed in config_gen.json (for information)
    if git diff --name-only $CURRENT_VERSION..HEAD | grep -q "config_gen.json"; then
        echo ""
        echo "⚠️  Note: config_gen.json was updated"
        echo "   Your personal settings in ~/.wordclock/config_loc.json are safe"
        echo "   To see what changed: git diff $CURRENT_VERSION..HEAD config_gen.json"
    fi
    
    # Show all changes
    echo ""
    echo "📋 Files updated:"
    git diff --name-only $CURRENT_VERSION..HEAD | sed 's/^/   - /'
    
else
    echo "❌ Update failed. You might have local changes."
    echo "Try: cd $INSTALL_DIR && git stash && git pull --ff-only"
fi

echo ""
echo "✨ Update complete! Your config is in ~/.wordclock/config_loc.json"
