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
    DASHBOARD_CONFIG="$DASHBOARD_NGINX_CONF_DIR/${DASHBOARD_NAME}_dashboard.conf"
    
    if [ -f "$DASHBOARD_CONFIG" ]; then
        cp "$DASHBOARD_CONFIG" "$MAIN_NGINX_CONF_DIR/${DASHBOARD_NAME}_dashboard.conf"
        echo "   ✓ Copied: ${DASHBOARD_NAME}_dashboard.conf"
        COPIED_COUNT=$((COPIED_COUNT + 1))
    else
        echo "   ⚠️  Config not found: ${DASHBOARD_NAME}_dashboard.conf"
        echo "      Run: ./scripts/generate_nginx_config.sh $DASHBOARD_NAME"
    fi
done <<< "$DASHBOARDS"

echo "✅ Copied $COPIED_COUNT dashboard nginx configuration(s)"

# Reload nginx if running
if docker ps --format "{{.Names}}" | grep -q "visstore_nginx"; then
    echo "🔄 Reloading nginx..."
    if docker exec visstore_nginx nginx -t; then
        docker exec visstore_nginx nginx -s reload
        echo "✅ Nginx reloaded with dashboard configurations"
    else
        echo "❌ Nginx configuration test failed"
        exit 1
    fi
else
    echo "⚠️  Nginx container (visstore_nginx) not found"
    echo "   Configurations will be active when nginx starts"
fi

echo ""
echo "✅ Dashboard nginx setup complete!"

