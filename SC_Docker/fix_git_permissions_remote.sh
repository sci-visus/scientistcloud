#!/bin/bash

# Quick fix for git permission issues on remote server
# Removes problematic vendor/auth0 directory and resets git state

set -e

echo "🔧 Fixing git permission issues..."
echo ""

# Navigate to the repository root
cd ~/ScientistCloud2.0/scientistcloud

# Check current git status
echo "📋 Current git status:"
git status --short | head -10 || true
echo ""

# Remove the problematic vendor/auth0 directory
VENDOR_AUTH0_DIR="SC_Web/vendor/auth0"
if [ -d "$VENDOR_AUTH0_DIR" ]; then
    echo "🗑️  Removing $VENDOR_AUTH0_DIR..."
    sudo rm -rf "$VENDOR_AUTH0_DIR" 2>/dev/null || rm -rf "$VENDOR_AUTH0_DIR" 2>/dev/null || {
        echo "   ⚠️  Could not remove directory, trying with force..."
        # If still can't remove, try to fix permissions first
        sudo chown -R $(whoami):$(id -gn) "$VENDOR_AUTH0_DIR" 2>/dev/null || true
        rm -rf "$VENDOR_AUTH0_DIR" 2>/dev/null || {
            echo "   ❌ Still cannot remove. Try manually: sudo rm -rf $VENDOR_AUTH0_DIR"
            exit 1
        }
    }
    echo "   ✓ Removed successfully"
else
    echo "   ℹ️  Directory doesn't exist (already removed?)"
fi

# Clean up git index for this directory
echo ""
echo "🧹 Cleaning git index..."
git rm -r --cached "$VENDOR_AUTH0_DIR" 2>/dev/null || true

# Reset any uncommitted changes in vendor directory
echo ""
echo "🔄 Resetting vendor directory changes..."
git checkout -- SC_Web/vendor/ 2>/dev/null || true

# Now try to pull
echo ""
echo "📥 Attempting git pull..."
if git pull; then
    echo ""
    echo "✅ Git pull successful!"
    echo ""
    echo "💡 If vendor/auth0 is needed, it will be recreated by composer"
    echo "   Run: cd SC_Web && composer install"
else
    echo ""
    echo "❌ Git pull failed"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if there are other permission issues:"
    echo "   find SC_Web/vendor -type f ! -writable"
    echo ""
    echo "2. Remove entire vendor directory and reinstall:"
    echo "   rm -rf SC_Web/vendor"
    echo "   cd SC_Web && composer install"
    echo ""
    echo "3. Or force reset:"
    echo "   git fetch origin"
    echo "   git reset --hard origin/main"
    exit 1
fi

