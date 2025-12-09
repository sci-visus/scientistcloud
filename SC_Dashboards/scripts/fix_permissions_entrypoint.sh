#!/bin/bash
# Entrypoint script to fix permissions for dashboard sessions
# This script runs as root to fix permissions, then switches to bokehuser

set -e

# Function to fix permissions on a directory
fix_dir_permissions() {
    local dir="$1"
    if [ -d "$dir" ]; then
        # Try to set group to www-data and add write permissions for group
        chgrp -R www-data "$dir" 2>/dev/null || echo "⚠️ Could not change group of $dir"
        chmod -R g+w "$dir" 2>/dev/null || echo "⚠️ Could not add write permissions to $dir"
        echo "✅ Fixed permissions for $dir"
    fi
}

# Fix permissions on visus_datasets mount point
if [ -d "/mnt/visus_datasets" ]; then
    echo "🔧 Fixing permissions on /mnt/visus_datasets..."
    
    # Fix permissions on upload directory
    if [ -d "/mnt/visus_datasets/upload" ]; then
        # For each dataset directory, ensure sessions subdirectory is writable
        find /mnt/visus_datasets/upload -maxdepth 1 -type d | while read dataset_dir; do
            if [ "$dataset_dir" != "/mnt/visus_datasets/upload" ]; then
                sessions_dir="${dataset_dir}/sessions"
                if [ ! -d "$sessions_dir" ]; then
                    # Try to create it
                    mkdir -p "$sessions_dir" 2>/dev/null || echo "⚠️ Could not create $sessions_dir"
                fi
                if [ -d "$sessions_dir" ]; then
                    fix_dir_permissions "$sessions_dir"
                fi
            fi
        done
    fi
fi

# Switch to bokehuser and execute the command
exec gosu bokehuser "$@"
