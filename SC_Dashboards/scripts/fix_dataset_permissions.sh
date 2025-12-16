#!/bin/bash
# Script to fix permissions on dataset directories so dashboards can write sessions
# Run this on the host server (not in container)
# Usage: ./fix_dataset_permissions.sh

set -e

VISUS_DATASETS_DIR="${VISUS_DATASETS:-/mnt/visus_datasets}"

if [ ! -d "$VISUS_DATASETS_DIR/upload" ]; then
    echo "❌ Directory not found: $VISUS_DATASETS_DIR/upload"
    echo "   Set VISUS_DATASETS environment variable if using a different path"
    exit 1
fi

echo "🔧 Fixing permissions on dataset directories..."
echo "   Target: $VISUS_DATASETS_DIR/upload"

# Get www-data group ID (might be 33 on Debian/Ubuntu)
WWW_DATA_GID=$(getent group www-data | cut -d: -f3 2>/dev/null || echo "33")

# Fix permissions on upload directory and all subdirectories
echo "   Setting group ownership to www-data (GID: $WWW_DATA_GID)..."
sudo chgrp -R www-data "$VISUS_DATASETS_DIR/upload" || {
    echo "⚠️  Could not change group ownership. Trying with numeric GID..."
    sudo chgrp -R "$WWW_DATA_GID" "$VISUS_DATASETS_DIR/upload" || {
        echo "❌ Failed to set group ownership. You may need to:"
        echo "   1. Create www-data group: sudo groupadd -g 33 www-data"
        echo "   2. Or use a different group that the dashboard container uses"
        exit 1
    }
}

echo "   Adding group write permissions..."
sudo chmod -R g+w "$VISUS_DATASETS_DIR/upload"

# Set setgid bit on directories so new files inherit group
echo "   Setting setgid bit on directories..."
find "$VISUS_DATASETS_DIR/upload" -type d -exec sudo chmod g+s {} \;

echo "✅ Permissions fixed!"
echo ""
echo "📋 Summary:"
echo "   - Group ownership: www-data"
echo "   - Permissions: g+w (group writable)"
echo "   - Setgid: enabled (new files inherit group)"
echo ""
echo "💡 Dashboard containers should now be able to create sessions directories"

