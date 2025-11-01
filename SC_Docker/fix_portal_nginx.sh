#!/bin/bash

# Quick script to fix portal nginx configuration
# This can be run manually on the server

echo "🔧 Fixing portal nginx configuration..."

# Try to find the VisusDataPortalPrivate Docker directory
VISUS_DOCKER_PATH=""
for path in \
    "$HOME/VisStoreClone/visus-dataportal-private/Docker" \
    "$HOME/visus-dataportal-private/Docker" \
    "$HOME/VisStoreCode/visus-dataportal-private/Docker" \
    "/home/amy/VisStoreClone/visus-dataportal-private/Docker" \
    "/home/amy/VisStoreCode/visus-dataportal-private/Docker"; do
    if [ -d "$path" ]; then
        VISUS_DOCKER_PATH="$path"
        echo "✓ Found Docker directory at: $path"
        break
    fi
done

# If still not found, try to detect from running nginx container
if [ -z "$VISUS_DOCKER_PATH" ]; then
    echo "Searching for Docker directory from nginx container..."
    # Get the mounted volume path
    MOUNT_PATH=$(docker inspect visstore_nginx 2>/dev/null | grep -o '"/[^"]*/nginx/conf\.d"' | head -1 | tr -d '"' 2>/dev/null)
    if [ -n "$MOUNT_PATH" ]; then
        VISUS_DOCKER_PATH=$(dirname "$MOUNT_PATH" 2>/dev/null || echo "")
        if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
            echo "✓ Found Docker directory at: $VISUS_DOCKER_PATH"
        fi
    fi
fi

# If still not found, search the filesystem
if [ -z "$VISUS_DOCKER_PATH" ]; then
    echo "Searching filesystem for setup_portal_nginx.sh..."
    SEARCH_RESULT=$(find "$HOME" -name "setup_portal_nginx.sh" -type f 2>/dev/null | head -1)
    if [ -n "$SEARCH_RESULT" ]; then
        VISUS_DOCKER_PATH=$(dirname "$SEARCH_RESULT")
        echo "✓ Found setup_portal_nginx.sh at: $VISUS_DOCKER_PATH"
    fi
fi

# Run the setup script
if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
    cd "$VISUS_DOCKER_PATH"
    
    if [ -f "./setup_portal_nginx.sh" ]; then
        echo "Running setup_portal_nginx.sh..."
        ./setup_portal_nginx.sh
    elif [ -f "./setup_ssl.sh" ]; then
        echo "Running portal config from setup_ssl.sh..."
        # Extract and run setup_portal_config function
        bash -c "$(grep -A 76 '^setup_portal_config()' ./setup_ssl.sh | grep -v '^setup_portal_config()' | sed 's/^setup_portal_config() {/setup_portal_config() {/')" && setup_portal_config
    else
        echo "❌ Neither setup_portal_nginx.sh nor setup_ssl.sh found"
        echo "Directory contents:"
        ls -la
        exit 1
    fi
else
    echo "❌ Could not find VisusDataPortalPrivate Docker directory"
    echo ""
    echo "Please manually find and run the setup script:"
    echo "  1. Find the Docker directory: find ~ -name 'default.conf' -path '*/nginx/conf.d/*' 2>/dev/null"
    echo "  2. cd to that Docker directory"
    echo "  3. Run: ./setup_portal_nginx.sh"
    echo ""
    echo "Or if setup_portal_nginx.sh doesn't exist, add portal config manually to nginx/conf.d/default.conf"
    exit 1
fi

