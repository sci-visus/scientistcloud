#!/bin/bash

# Fix permissions on vendor directory to allow git operations
# This script removes extended attributes and fixes ownership/permissions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="$SCRIPT_DIR/../SC_Web/vendor"

echo "🔧 Fixing permissions on vendor directory..."
echo "   Target: $VENDOR_DIR"

if [ ! -d "$VENDOR_DIR" ]; then
    echo "❌ Vendor directory not found: $VENDOR_DIR"
    exit 1
fi

# Get current user - detect original user if running with sudo
if [ -n "$SUDO_USER" ]; then
    CURRENT_USER="$SUDO_USER"
    CURRENT_GROUP=$(id -gn "$SUDO_USER")
else
    CURRENT_USER=$(whoami)
    CURRENT_GROUP=$(id -gn)
fi

echo "   Current user: $CURRENT_USER"
echo "   Current group: $CURRENT_GROUP"

# Remove extended attributes (macOS quarantine, etc.)
# On Linux, this is usually not needed, but we'll try anyway
echo ""
echo "📋 Removing extended attributes (if any)..."
if command -v xattr >/dev/null 2>&1; then
    find "$VENDOR_DIR" -type f -exec xattr -c {} \; 2>/dev/null || true
    find "$VENDOR_DIR" -type d -exec xattr -c {} \; 2>/dev/null || true
    echo "   ✓ Extended attributes removed (if present)"
elif command -v getfattr >/dev/null 2>&1; then
    # Linux alternative: remove extended attributes using getfattr/setfattr
    find "$VENDOR_DIR" -type f -exec setfattr -h -x security.selinux {} \; 2>/dev/null || true
    echo "   ✓ Extended attributes removed (if present)"
else
    echo "   ℹ️  No extended attribute tools found (normal on Linux)"
fi

# Fix ownership
echo ""
echo "📋 Fixing ownership..."
# Try with sudo first (common on Linux servers)
if sudo -n true 2>/dev/null; then
    # Sudo available without password prompt
    sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$VENDOR_DIR" 2>/dev/null && {
        echo "   ✓ Ownership fixed with sudo"
    } || {
        echo "   Trying without sudo..."
        chown -R "$CURRENT_USER:$CURRENT_GROUP" "$VENDOR_DIR" 2>/dev/null && {
            echo "   ✓ Ownership fixed"
        } || {
            echo "   ⚠️  Could not change ownership - files may be owned by another user"
            echo "   Current ownership:"
            ls -ld "$VENDOR_DIR" | awk '{print "      " $3 ":" $4 " " $1}'
        }
    }
else
    # Try without sudo first
    chown -R "$CURRENT_USER:$CURRENT_GROUP" "$VENDOR_DIR" 2>/dev/null && {
        echo "   ✓ Ownership fixed"
    } || {
        echo "   ⚠️  Could not change ownership without sudo"
        echo "   You may need to run: sudo chown -R $CURRENT_USER:$CURRENT_GROUP $VENDOR_DIR"
        echo "   Current ownership:"
        ls -ld "$VENDOR_DIR" | awk '{print "      " $3 ":" $4 " " $1}'
    }
fi

# Fix permissions - make files writable
echo ""
echo "📋 Fixing file permissions..."
find "$VENDOR_DIR" -type f -exec chmod 644 {} \; 2>/dev/null || true
find "$VENDOR_DIR" -type d -exec chmod 755 {} \; 2>/dev/null || true

# Make sure we can write to the directory
chmod -R u+w "$VENDOR_DIR" 2>/dev/null || true

echo ""
echo "✅ Permissions fixed!"
echo ""
echo "📋 Summary:"
echo "   - Ownership: $CURRENT_USER:$CURRENT_GROUP"
echo "   - File permissions: 644 (rw-r--r--)"
echo "   - Directory permissions: 755 (rwxr-xr-x)"
echo "   - Extended attributes: removed"
echo ""
echo "💡 You should now be able to run git operations"
echo ""
echo "Try running your git command again:"
echo "   git reset --hard origin/main"
echo "   or"
echo "   git pull"

