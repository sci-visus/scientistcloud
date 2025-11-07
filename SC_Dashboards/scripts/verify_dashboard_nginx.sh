#!/bin/bash
# Verify and fix dashboard nginx configuration setup
# This script checks if dashboard configs are in the right place and fixes issues

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
DASHBOARD_SUBDIR="$MAIN_NGINX_CONF_DIR/dashboards"

echo "🔍 Verifying dashboard nginx configuration..."
echo "   Main nginx conf.d: $MAIN_NGINX_CONF_DIR"
echo "   Dashboard configs source: $DASHBOARD_NGINX_CONF_DIR"
echo "   Dashboard configs target: $DASHBOARD_SUBDIR"

# Check if source directory exists
if [ ! -d "$DASHBOARD_NGINX_CONF_DIR" ]; then
    echo "❌ Dashboard config source directory not found: $DASHBOARD_NGINX_CONF_DIR"
    echo "   Run: ./scripts/generate_nginx_config.sh for each dashboard first"
    exit 1
fi

# Check if main nginx conf.d exists
if [ ! -d "$MAIN_NGINX_CONF_DIR" ]; then
    echo "❌ Main nginx conf.d directory not found: $MAIN_NGINX_CONF_DIR"
    exit 1
fi

# Create dashboard subdirectory if it doesn't exist
mkdir -p "$DASHBOARD_SUBDIR" 2>/dev/null || true

# Check if dashboard configs exist in source
echo "   Checking for dashboard configs in source..."
DASHBOARD_CONFIGS=$(find "$DASHBOARD_NGINX_CONF_DIR" -name "*_dashboard.conf" -type f 2>/dev/null | wc -l)
if [ "$DASHBOARD_CONFIGS" -eq 0 ]; then
    echo "   ⚠️  No dashboard configs found in source directory"
    echo "   Run: ./scripts/generate_nginx_config.sh for each dashboard"
else
    echo "   ✅ Found $DASHBOARD_CONFIGS dashboard config(s) in source"
fi

# Check if dashboard configs exist in target
echo "   Checking for dashboard configs in target..."
TARGET_CONFIGS=$(find "$DASHBOARD_SUBDIR" -name "*_dashboard.conf" -type f 2>/dev/null | wc -l)
if [ "$TARGET_CONFIGS" -eq 0 ]; then
    echo "   ⚠️  No dashboard configs found in target directory"
    echo "   Run: ./scripts/setup_dashboards_nginx.sh \"$VISUS_DOCKER_PATH\""
else
    echo "   ✅ Found $TARGET_CONFIGS dashboard config(s) in target"
fi

# List configs in both locations
echo ""
echo "📋 Source configs:"
ls -1 "$DASHBOARD_NGINX_CONF_DIR"/*_dashboard.conf 2>/dev/null || echo "   (none)"

echo ""
echo "📋 Target configs:"
ls -1 "$DASHBOARD_SUBDIR"/*_dashboard.conf 2>/dev/null || echo "   (none)"

# Check if nginx config includes dashboard configs
echo ""
echo "🔍 Checking nginx main config..."
if grep -q "include.*dashboards.*_dashboard.conf" "$MAIN_NGINX_CONF_DIR"/scientistcloud.conf 2>/dev/null; then
    echo "   ✅ Main nginx config includes dashboard configs"
else
    echo "   ⚠️  Main nginx config does NOT include dashboard configs"
    echo "   Expected line: include /etc/nginx/conf.d/dashboards/*_dashboard.conf;"
fi

# Check if dashboard containers are running
echo ""
echo "🔍 Checking dashboard containers..."
if docker ps --format "{{.Names}}" | grep -q "dashboard_"; then
    echo "   ✅ Dashboard containers are running:"
    docker ps --format "  {{.Names}} - {{.Status}}" | grep "dashboard_" || true
else
    echo "   ⚠️  No dashboard containers are running"
    echo "   Run: docker-compose -f dashboards-docker-compose.yml up -d"
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "To fix issues, run:"
echo "  1. Generate configs: ./scripts/generate_nginx_config.sh <dashboard-name>"
echo "  2. Copy configs: ./scripts/setup_dashboards_nginx.sh \"$VISUS_DOCKER_PATH\""
echo "  3. Reload nginx: docker exec visstore_nginx nginx -s reload"


