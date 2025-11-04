#!/bin/bash
# Setup dashboard nginx configurations in main nginx
# Copies dashboard nginx configs from SC_Dashboards to main nginx conf.d
# 
# NOTE: This is different from the old dashboard setup which embedded
# configurations directly in default.conf.https and default.conf.template
# inside the server blocks. New dashboards use separate .conf files in
# conf.d/ which are automatically included by nginx.
#
# Usage: ./setup_dashboards_nginx.sh [visus_docker_path]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"

# Find VisusDataPortalPrivate Docker directory
VISUS_DOCKER_PATH="$1"

if [ -z "$VISUS_DOCKER_PATH" ]; then
    # Try to find it using same logic as allServicesStart.sh
    if [ -n "$VISUS_DOCKER" ]; then
        VISUS_DOCKER_PATH="${VISUS_DOCKER%/ag-explorer}"
        VISUS_DOCKER_PATH="${VISUS_DOCKER_PATH%/ag-explorer/}"
        if [[ "$VISUS_DOCKER_PATH" != */Docker ]]; then
            if [ -n "$VISUS_CODE" ]; then
                VISUS_DOCKER_PATH="$VISUS_CODE/Docker"
            fi
        fi
    fi
    
    if [ -z "$VISUS_DOCKER_PATH" ] && [ -n "$VISUS_CODE" ]; then
        VISUS_DOCKER_PATH="$VISUS_CODE/Docker"
    fi
    
    if [ -z "$VISUS_DOCKER_PATH" ] || [ ! -d "$VISUS_DOCKER_PATH" ]; then
        for path in \
            "$HOME/VisStoreClone/visus-dataportal-private/Docker" \
            "$HOME/visus-dataportal-private/Docker" \
            "$HOME/VisStoreCode/visus-dataportal-private/Docker" \
            "/home/amy/VisStoreClone/visus-dataportal-private/Docker" \
            "/home/amy/VisStoreCode/visus-dataportal-private/Docker"; do
            if [ -d "$path" ]; then
                VISUS_DOCKER_PATH="$path"
                break
            fi
        done
    fi
fi

if [ -z "$VISUS_DOCKER_PATH" ] || [ ! -d "$VISUS_DOCKER_PATH" ]; then
    echo "❌ VisusDataPortalPrivate Docker directory not found"
    echo "   Please provide path as argument or set VISUS_DOCKER environment variable"
    exit 1
fi

MAIN_NGINX_CONF_DIR="$VISUS_DOCKER_PATH/nginx/conf.d"
DASHBOARD_NGINX_CONF_DIR="$SCRIPT_DIR/../../SC_Docker/nginx/conf.d"

if [ ! -d "$MAIN_NGINX_CONF_DIR" ]; then
    echo "❌ Main nginx conf.d directory not found: $MAIN_NGINX_CONF_DIR"
    exit 1
fi

if [ ! -d "$DASHBOARD_NGINX_CONF_DIR" ]; then
    echo "❌ Dashboard nginx conf.d directory not found: $DASHBOARD_NGINX_CONF_DIR"
    echo "   Generating nginx configs first..."
    exit 1
fi

echo "📋 Setting up dashboard nginx configurations..."
echo "   Source: $DASHBOARD_NGINX_CONF_DIR"
echo "   Target: $MAIN_NGINX_CONF_DIR"

# Check nginx status first - if restarting, stop it to break the loop
if docker ps --format "{{.Names}}" | grep -q "visstore_nginx"; then
    NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' visstore_nginx 2>/dev/null || echo "not-found")
    if [ "$NGINX_STATUS" = "restarting" ]; then
        echo "⚠️  Nginx container is restarting (likely due to bad configs)"
        echo "   Stopping nginx to break restart loop..."
        docker stop visstore_nginx 2>/dev/null || true
        sleep 2
        echo "   ✅ Nginx stopped"
    fi
fi

# Clean up old/conflicting config files BEFORE copying new ones
# This prevents nginx from picking up bad configs during restart
echo "   Cleaning up old dashboard configs..."
REMOVED_COUNT=0

if [ -d "$MAIN_NGINX_CONF_DIR" ]; then
    # Remove files without server blocks (old format that causes errors)
    while IFS= read -r OLD_CONFIG; do
        if [ -f "$OLD_CONFIG" ]; then
            # Check if file doesn't start with a server block
            if ! grep -q "^server {" "$OLD_CONFIG" 2>/dev/null; then
                echo "   🗑️  Removing old format config (no server block): $(basename "$OLD_CONFIG")"
                rm -f "$OLD_CONFIG" 2>/dev/null || true
                REMOVED_COUNT=$((REMOVED_COUNT + 1))
            fi
        fi
    done < <(find "$MAIN_NGINX_CONF_DIR" -maxdepth 1 -name "*_dashboard.conf" -o -name "*Dashboard*.conf" 2>/dev/null || true)
    
    # Remove uppercase duplicates (e.g., 3DPlotly_dashboard.conf) if lowercase versions exist
    for config_file in "$MAIN_NGINX_CONF_DIR"/*_dashboard.conf; do
        if [ -f "$config_file" ]; then
            basename_config=$(basename "$config_file")
            lowercase_basename=$(echo "$basename_config" | tr '[:upper:]' '[:lower:]')
            if [ "$basename_config" != "$lowercase_basename" ] && [ -f "$MAIN_NGINX_CONF_DIR/$lowercase_basename" ]; then
                echo "   🗑️  Removing uppercase duplicate: $basename_config (lowercase version exists)"
                rm -f "$config_file" 2>/dev/null || true
                REMOVED_COUNT=$((REMOVED_COUNT + 1))
            fi
        fi
    done
fi

if [ $REMOVED_COUNT -gt 0 ]; then
    echo "   ✅ Removed $REMOVED_COUNT old/duplicate config file(s)"
fi

# Load dashboard registry
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"
if [ ! -f "$REGISTRY_FILE" ]; then
    echo "❌ Dashboard registry not found: $REGISTRY_FILE"
    exit 1
fi

# Copy nginx configs for all enabled dashboards
COPIED_COUNT=0
DASHBOARDS=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' "$REGISTRY_FILE" 2>/dev/null || echo "")

if [ -z "$DASHBOARDS" ]; then
    echo "⚠️  No enabled dashboards found in registry"
    exit 0
fi

while IFS= read -r DASHBOARD_NAME; do
    # Generate lowercase name and remove trailing "_dashboard" if present
    # (matches logic in generate_nginx_config.sh)
    DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
    DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME_LOWER" | sed 's/_dashboard$//')
    OUTPUT_NAME="${DASHBOARD_NAME_LOWER}_dashboard.conf"
    
    # Try exact name first, then lowercase variant (nginx configs use lowercase names)
    DASHBOARD_CONFIG="$DASHBOARD_NGINX_CONF_DIR/${DASHBOARD_NAME}_dashboard.conf"
    
    # If not found, try lowercase variant (this is what generate_nginx_config.sh creates)
    if [ ! -f "$DASHBOARD_CONFIG" ]; then
        DASHBOARD_CONFIG="$DASHBOARD_NGINX_CONF_DIR/${OUTPUT_NAME}"
    fi
    
    if [ -f "$DASHBOARD_CONFIG" ]; then
        # Use consistent lowercase name in main nginx conf.d to avoid conflicts
        cp "$DASHBOARD_CONFIG" "$MAIN_NGINX_CONF_DIR/${OUTPUT_NAME}"
        echo "   ✓ Copied: ${OUTPUT_NAME} (from ${DASHBOARD_NAME})"
        COPIED_COUNT=$((COPIED_COUNT + 1))
    else
        echo "   ⚠️  Config not found for ${DASHBOARD_NAME}"
        echo "      Tried: ${DASHBOARD_NAME}_dashboard.conf"
        echo "      Tried: ${OUTPUT_NAME}"
        echo "      Run: ./scripts/generate_nginx_config.sh $DASHBOARD_NAME"
    fi
done <<< "$DASHBOARDS"

echo "✅ Copied $COPIED_COUNT dashboard nginx configuration(s)"

# Now test and start/reload nginx
# First, test the configuration using a temporary container (before touching the real one)
echo "   Testing nginx configuration..."
if docker run --rm -v "$VISUS_DOCKER_PATH/nginx:/etc/nginx:ro" nginx:alpine nginx -t 2>&1 | grep -q "syntax is ok"; then
    echo "   ✅ Configuration test passed"
    
    # Check if nginx container exists
    if docker ps -a --format "{{.Names}}" | grep -q "visstore_nginx"; then
        # Container exists - check if it's running
        NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' visstore_nginx 2>/dev/null || echo "not-found")
        
        if [ "$NGINX_STATUS" = "running" ]; then
            # Container is running - reload it
            echo "🔄 Reloading nginx..."
            docker exec visstore_nginx nginx -s reload
            echo "✅ Nginx reloaded with dashboard configurations"
        else
            # Container exists but not running - start it
            echo "🔄 Starting nginx container..."
            docker start visstore_nginx 2>/dev/null || true
            sleep 3
            
            # Verify it started
            NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' visstore_nginx 2>/dev/null || echo "not-found")
            if [ "$NGINX_STATUS" = "running" ]; then
                echo "✅ Nginx container started successfully"
            else
                echo "⚠️  Nginx container status: $NGINX_STATUS"
                echo "   Check logs: docker logs visstore_nginx"
            fi
        fi
    else
        echo "ℹ️  Nginx container not found - configurations will be active when nginx starts"
    fi
else
    echo "❌ Nginx configuration test failed"
    echo "   Error details:"
    docker run --rm -v "$VISUS_DOCKER_PATH/nginx:/etc/nginx:ro" nginx:alpine nginx -t 2>&1 | sed 's/^/      /'
    echo ""
    echo "   Configurations were copied but nginx cannot start/reload"
    echo "   Fix the errors above before starting nginx"
    exit 1
fi

echo ""
echo "✅ Dashboard nginx setup complete!"

