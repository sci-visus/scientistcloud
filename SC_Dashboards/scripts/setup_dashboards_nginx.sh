#!/bin/bash
# Setup dashboard nginx configurations in main nginx
# Copies dashboard nginx configs from SC_Dashboards to main nginx conf.d
# 
# NOTE: This is different from the old dashboard setup which embedded
# configurations directly in default.conf.https and default.conf.template
# inside the server blocks. New dashboards use separate .conf files in
# conf.d/ which are automatically included by nginx.
#
# Usage:
#   ./setup_dashboards_nginx.sh sc
#     → SC-native: scientistcloud/SC_Docker/nginx/conf.d/dashboards/ (reload scientistcloud-nginx)
#   ./setup_dashboards_nginx.sh [visus_docker_path]
#     → Legacy: copy into VisusDataPortalPrivate Docker/nginx (reload visstore_nginx)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
SC_DOCKER_DIR="$(cd "$SCRIPT_DIR/../../SC_Docker" && pwd)"

# Target: SC-native (recommended) or legacy VisusDataPortalPrivate
NGINX_TARGET="${1:-}"
USE_SC_NATIVE=false
VISUS_DOCKER_PATH=""

if [ "$NGINX_TARGET" = "sc" ] || [ "$NGINX_TARGET" = "--sc" ]; then
    USE_SC_NATIVE=true
elif [ -n "$NGINX_TARGET" ]; then
    VISUS_DOCKER_PATH="$NGINX_TARGET"
fi

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

if [ "$USE_SC_NATIVE" = true ]; then
    MAIN_NGINX_CONF_DIR="$SC_DOCKER_DIR/nginx/conf.d"
    DASHBOARD_NGINX_CONF_DIR="$SC_DOCKER_DIR/nginx/conf.d"
    DASHBOARD_SUBDIR="$MAIN_NGINX_CONF_DIR/dashboards"
    NGINX_CONTAINER_NAME="${SC_NGINX_CONTAINER:-scientistcloud-nginx}"
    NGINX_TEST_MOUNT="$SC_DOCKER_DIR/nginx"
    USE_SC_NGINX_TEST=true
    echo "📋 SC-native nginx target: $DASHBOARD_SUBDIR"
else
    if [ -z "$VISUS_DOCKER_PATH" ] || [ ! -d "$VISUS_DOCKER_PATH" ]; then
        echo "❌ VisusDataPortalPrivate Docker directory not found"
        echo "   Use: ./setup_dashboards_nginx.sh sc   (ScientistCloud 2.0 — recommended)"
        echo "   Or provide legacy path: ./setup_dashboards_nginx.sh /path/to/VisusDataPortalPrivate/Docker"
        exit 1
    fi
    MAIN_NGINX_CONF_DIR="$VISUS_DOCKER_PATH/nginx/conf.d"
    DASHBOARD_NGINX_CONF_DIR="$SC_DOCKER_DIR/nginx/conf.d"
    DASHBOARD_SUBDIR="$MAIN_NGINX_CONF_DIR/dashboards"
    NGINX_CONTAINER_NAME="visstore_nginx"
    NGINX_TEST_MOUNT="$VISUS_DOCKER_PATH/nginx"
    USE_SC_NGINX_TEST=false
    echo "📋 Legacy VisusDataPortalPrivate nginx target: $DASHBOARD_SUBDIR"
fi

if [ ! -d "$MAIN_NGINX_CONF_DIR" ]; then
    echo "❌ Main nginx conf.d directory not found: $MAIN_NGINX_CONF_DIR"
    exit 1
fi

# Create dashboard subdirectory if it doesn't exist
mkdir -p "$DASHBOARD_SUBDIR" 2>/dev/null || true

if [ ! -d "$DASHBOARD_NGINX_CONF_DIR" ]; then
    echo "❌ Dashboard nginx conf.d directory not found: $DASHBOARD_NGINX_CONF_DIR"
    echo "   Generating nginx configs first..."
    exit 1
fi

echo "📋 Setting up dashboard nginx configurations..."
echo "   Source: $DASHBOARD_NGINX_CONF_DIR"
echo "   Target: $DASHBOARD_SUBDIR"
echo "   (Dashboard configs are location blocks, stored in subdirectory to avoid http-level includes)"

# Check nginx status first - if restarting, stop it to break the loop
if docker ps --format "{{.Names}}" | grep -q "^${NGINX_CONTAINER_NAME}$"; then
    NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' "$NGINX_CONTAINER_NAME" 2>/dev/null || echo "not-found")
    if [ "$NGINX_STATUS" = "restarting" ]; then
        echo "⚠️  Nginx container is restarting (likely due to bad configs)"
        echo "   Stopping nginx to break restart loop..."
        docker stop "$NGINX_CONTAINER_NAME" 2>/dev/null || true
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
    
    # Also clean up dashboard subdirectory
    if [ -d "$DASHBOARD_SUBDIR" ]; then
        find "$DASHBOARD_SUBDIR" -name "*_dashboard.conf" -delete 2>/dev/null || true
    fi
    
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
        # Clean up any artifacts before copying
        # Remove lines with "f}}/d" (sed artifact) and ensure proper structure
        TEMP_COPY=$(mktemp)
        grep -v '^f\}\}\/d$' "$DASHBOARD_CONFIG" > "$TEMP_COPY"
        
        # Ensure file ends with closing brace
        if ! tail -1 "$TEMP_COPY" | grep -qE '^[[:space:]]*}[[:space:]]*$'; then
            # Count braces to see if we need to add one
            OPEN_COUNT=$(grep -v '^[[:space:]]*#' "$TEMP_COPY" | grep -o '{' | wc -l)
            CLOSE_COUNT=$(grep -v '^[[:space:]]*#' "$TEMP_COPY" | grep -o '}' | wc -l)
            if [ "$OPEN_COUNT" -gt "$CLOSE_COUNT" ]; then
                echo "" >> "$TEMP_COPY"
                echo "}" >> "$TEMP_COPY"
            fi
        fi
        
        cp "$TEMP_COPY" "$DASHBOARD_SUBDIR/${OUTPUT_NAME}"
        rm -f "$TEMP_COPY"
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

# Auth gate (login redirect for /dashboard/*) — must be present when dashboards use auth_request
AUTH_GATE_SRC="$DASHBOARD_NGINX_CONF_DIR/dashboard_auth_gate.conf"
if [ -f "$AUTH_GATE_SRC" ]; then
    cp "$AUTH_GATE_SRC" "$DASHBOARD_SUBDIR/dashboard_auth_gate.conf"
    echo "   ✓ Copied: dashboard_auth_gate.conf (required for auth_request)"
else
    echo "   ⚠️  Missing $AUTH_GATE_SRC — /dashboard/* will return 500 until this file exists"
fi

# Now test and start/reload nginx
# First, test the configuration using a temporary container (before touching the real one)
echo "   Testing nginx configuration..."
if [ "${USE_SC_NGINX_TEST:-false}" = true ]; then
    DOMAIN_NAME="${DOMAIN_NAME:-scientistcloud.com}"
    NGINX_TEST_OUTPUT=$(docker run --rm \
        -e DOMAIN_NAME="$DOMAIN_NAME" \
        -e NGINX_ENVSUBST_FILTER=DOMAIN_NAME \
        -v "$NGINX_TEST_MOUNT/nginx.conf:/etc/nginx/nginx.conf:ro" \
        -v "$NGINX_TEST_MOUNT/templates:/etc/nginx/templates:ro" \
        -v "$NGINX_TEST_MOUNT/includes:/etc/nginx/includes:ro" \
        -v "$DASHBOARD_SUBDIR:/etc/nginx/conf.d/dashboards:ro" \
        nginx:latest /docker-entrypoint.sh nginx -t 2>&1)
else
    NGINX_TEST_OUTPUT=$(docker run --rm -v "$NGINX_TEST_MOUNT:/etc/nginx:ro" nginx:alpine nginx -t 2>&1)
fi
NGINX_TEST_EXIT=$?

if echo "$NGINX_TEST_OUTPUT" | grep -q "syntax is ok"; then
    echo "   ✅ Configuration test passed"
    
    # Check if nginx container exists
    if docker ps -a --format "{{.Names}}" | grep -q "^${NGINX_CONTAINER_NAME}$"; then
        NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' "$NGINX_CONTAINER_NAME" 2>/dev/null || echo "not-found")
        
        if [ "$NGINX_STATUS" = "running" ]; then
            echo "🔄 Reloading $NGINX_CONTAINER_NAME..."
            docker exec "$NGINX_CONTAINER_NAME" nginx -s reload
            echo "✅ Nginx reloaded with dashboard configurations"
        else
            echo "🔄 Starting $NGINX_CONTAINER_NAME..."
            docker start "$NGINX_CONTAINER_NAME" 2>/dev/null || true
            sleep 3
            NGINX_STATUS=$(docker inspect --format='{{.State.Status}}' "$NGINX_CONTAINER_NAME" 2>/dev/null || echo "not-found")
            if [ "$NGINX_STATUS" = "running" ]; then
                echo "✅ Nginx container started successfully"
            else
                echo "⚠️  Nginx container status: $NGINX_STATUS"
                echo "   Check logs: docker logs $NGINX_CONTAINER_NAME"
            fi
        fi
    else
        echo "ℹ️  Nginx container '$NGINX_CONTAINER_NAME' not found — start with:"
        echo "   cd $SC_DOCKER_DIR && docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d scientistcloud-nginx"
    fi
else
    echo "❌ Nginx configuration test failed"
    echo "   Error details:"
    echo "$NGINX_TEST_OUTPUT" | sed 's/^/      /'
    echo ""
    echo "   Checking dashboard config files for issues..."
    # List the dashboard config files and check if they have closing braces
    for conf_file in "$MAIN_NGINX_CONF_DIR"/*_dashboard.conf; do
        if [ -f "$conf_file" ]; then
            echo "   Checking: $(basename "$conf_file")"
            if ! tail -1 "$conf_file" | grep -qE '^[[:space:]]*}[[:space:]]*$'; then
                echo "      ⚠️  Missing closing brace"
            fi
            if ! head -1 "$conf_file" | grep -q "server {"; then
                echo "      ⚠️  Missing server block"
            fi
        fi
    done
    echo ""
    echo "   Configurations were copied but nginx cannot start/reload"
    echo "   Fix the errors above before starting nginx"
    exit 1
fi

echo ""
echo "✅ Dashboard nginx setup complete!"

