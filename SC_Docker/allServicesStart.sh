#!/bin/bash
 
# For ScientistCloud 2.0, we need to start all the services in the correct order
# Usage: ./allServicesStart.sh [--skip-main|--portal-only]
#   --skip-main or --portal-only: Skip starting VisusDataPortalPrivate services

# Parse command line arguments
SKIP_MAIN_SERVICES=false

if [[ "$1" == "--skip-main" ]] || [[ "$1" == "--portal-only" ]]; then
    SKIP_MAIN_SERVICES=true
    echo "📋 Skipping VisusDataPortalPrivate services (portal-only mode)"
fi

# Source environment variables first
ENV_FILE="$HOME/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud"
if [ -f "$ENV_FILE" ]; then
    echo "📋 Loading environment variables from $ENV_FILE..."
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
    echo "✅ Environment variables loaded"
else
    echo "⚠️ Environment file not found: $ENV_FILE"
    echo "   Continuing without custom environment variables..."
fi

echo "🚀 Starting all ScientistCloud services..."

# Start Update SCLib_TryTest
echo "📦 Update SCLib_TryTest and copy env.scientistcloud to SCLib and SC Website..."
SCLIB_TRYTEST_DIR="$HOME/ScientistCloud2.0/SCLib_TryTest"
if [ -d "$SCLIB_TRYTEST_DIR" ]; then
    pushd "$SCLIB_TRYTEST_DIR"
    git fetch origin
    git reset --hard origin/main
    cp env.scientistcloud "$HOME/ScientistCloud2.0/scientistCloudLib/Docker/.env"
    cp env.scientistcloud "$HOME/ScientistCloud2.0/scientistcloud/SC_Docker/.env"
    popd
    echo "✅ Environment files copied"
else
    echo "⚠️ SCLib_TryTest directory not found: $SCLIB_TRYTEST_DIR"
fi

# Start SCLib services first
echo "📦 Starting SCLib services..."
SCLIB_DOCKER_DIR="$HOME/ScientistCloud2.0/scientistCloudLib/Docker"
if [ -d "$SCLIB_DOCKER_DIR" ]; then
    pushd "$SCLIB_DOCKER_DIR"
    git fetch origin
    git reset --hard origin/main
    ./start.sh clean
    ./start.sh up
    popd
    echo "✅ SCLib services started"
else
    echo "⚠️ SCLib Docker directory not found: $SCLIB_DOCKER_DIR"
fi

# Start Portal services
echo "🌐 Starting Portal services..."
PORTAL_DOCKER_DIR="$HOME/ScientistCloud2.0/scientistcloud/SC_Docker"
if [ -d "$PORTAL_DOCKER_DIR" ]; then
    pushd "$PORTAL_DOCKER_DIR"
    git fetch origin
    git reset --hard origin/main
    ./start.sh clean
    ./start.sh start
    popd
    echo "✅ Portal services started"
else
    echo "❌ Portal Docker directory not found: $PORTAL_DOCKER_DIR"
    exit 1
fi

# Find VisusDataPortalPrivate Docker directory
# Priority: 1) VISUS_DOCKER env var, 2) VISUS_CODE env var + /Docker, 3) Common paths, 4) Detect from container
VISUS_DOCKER_PATH=""

# Check if VISUS_DOCKER is set (might have /ag-explorer/ at end, so normalize to just /Docker)
if [ -n "$VISUS_DOCKER" ]; then
    # Remove trailing ag-explorer/ if present
    VISUS_DOCKER_PATH="${VISUS_DOCKER%/ag-explorer}"
    VISUS_DOCKER_PATH="${VISUS_DOCKER_PATH%/ag-explorer/}"
    # Ensure it ends with /Docker
    if [[ "$VISUS_DOCKER_PATH" != */Docker ]]; then
        # Try to construct from VISUS_CODE if available
        if [ -n "$VISUS_CODE" ]; then
            VISUS_DOCKER_PATH="$VISUS_CODE/Docker"
        fi
    fi
fi

# If still not found, try VISUS_CODE
if [ -z "$VISUS_DOCKER_PATH" ] && [ -n "$VISUS_CODE" ]; then
    VISUS_DOCKER_PATH="$VISUS_CODE/Docker"
fi

# If still not found, try common paths
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

# If still not found, try to detect from running nginx container
if [ -z "$VISUS_DOCKER_PATH" ] || [ ! -d "$VISUS_DOCKER_PATH" ]; then
    # Try to find where nginx config is mounted from
    NGINX_CONF_PATH=$(docker inspect visstore_nginx 2>/dev/null | grep -o '"/[^"]*/nginx/conf\.d"' | head -1 | tr -d '"' 2>/dev/null)
    if [ -n "$NGINX_CONF_PATH" ] && [ -d "$NGINX_CONF_PATH" ]; then
        # Extract the Docker directory path
        VISUS_DOCKER_PATH=$(dirname "$NGINX_CONF_PATH" 2>/dev/null || echo "")
    fi
fi

# Start main VisusDataPortalPrivate services (unless skipped)
if [ "$SKIP_MAIN_SERVICES" = false ]; then
    echo "🏠 Starting main VisusDataPortalPrivate services..."
    if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
        echo "   Using Docker directory: $VISUS_DOCKER_PATH"
        pushd "$VISUS_DOCKER_PATH"
        if [ -f "./sync_with_github.sh" ]; then
            ./sync_with_github.sh
        fi
        if [ -f "./scientistCloud_docker_start_fresh.sh" ]; then
            ./scientistCloud_docker_start_fresh.sh
        fi
        if [ -f "./setup_ssl.sh" ]; then
            ./setup_ssl.sh
        fi
        popd
        echo "✅ Main services started"
    else
        echo "❌ VisusDataPortalPrivate Docker directory not found"
        echo "   Searched for:"
        echo "     - VISUS_DOCKER environment variable"
        echo "     - VISUS_CODE/Docker environment variable"
        echo "     - Common paths: ~/VisStoreClone, ~/VisStoreCode, ~/visus-dataportal-private"
        echo "     - From running nginx container"
        echo ""
        echo "   To fix: Set VISUS_DOCKER or VISUS_CODE in env.scientistcloud file"
        echo "   Or use --skip-main or --portal-only flag to skip main services"
        exit 1
    fi
else
    echo "⏭️  Skipping main VisusDataPortalPrivate services (portal-only mode)"
fi

# Setup portal nginx configuration after all services are running
# Portal is part of ScientistCloud 2.0, so we should set it up even if main services are skipped
# We just need the VisusDataPortalPrivate path to copy nginx configs to the main nginx
if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
    echo "🔧 Setting up portal nginx configuration..."
    pushd "$VISUS_DOCKER_PATH"
    if [ -f "./setup_portal_nginx.sh" ]; then
        ./setup_portal_nginx.sh
        echo "✅ Portal nginx configuration updated"
    else
        echo "⚠️ setup_portal_nginx.sh not found"
        echo "   Portal routes may not work. Please ensure setup_portal_nginx.sh exists in $VISUS_DOCKER_PATH"
        # setup_ssl.sh should have called setup_portal_config at the end, but verify
        if docker ps --format "{{.Names}}" | grep -q "scientistcloud-portal"; then
            echo "   Portal container is running, but nginx config may be missing portal routes"
        fi
    fi
    popd
else
    echo "⚠️ Cannot setup portal nginx configuration - Docker directory not found"
    echo "   Portal may still work if nginx is already configured, but routes may need manual setup"
    echo "   To fix: Set VISUS_DOCKER or VISUS_CODE in env.scientistcloud file"
fi

# Setup and build dashboards
# NOTE: New dashboards use separate .conf files in nginx/conf.d/ (automatically included)
# Old dashboards are embedded in default.conf.https/default.conf.template inside server blocks
# Ports are assigned to avoid conflicts with old dashboards (see PORT_CONFLICTS.md)
echo "📊 Setting up and building dashboards..."
DASHBOARDS_DIR="$HOME/ScientistCloud2.0/scientistcloud/SC_Dashboards"
if [ -d "$DASHBOARDS_DIR" ]; then
    pushd "$DASHBOARDS_DIR"
    
    # Initialize all enabled dashboards (generate Dockerfiles and nginx configs)
    echo "   Initializing dashboards..."
    DASHBOARDS=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    if [ -n "$DASHBOARDS" ]; then
        while IFS= read -r DASHBOARD_NAME; do
            echo "   📦 Initializing $DASHBOARD_NAME..."
            ./scripts/init_dashboard.sh "$DASHBOARD_NAME" 2>&1 | grep -E "(✅|⚠️|❌|Error)" || true
        done <<< "$DASHBOARDS"
    fi
    
    # Build all enabled dashboards
    echo "   Building dashboard Docker images..."
    if [ -n "$DASHBOARDS" ]; then
        while IFS= read -r DASHBOARD_NAME; do
            echo "   🐳 Building $DASHBOARD_NAME..."
            ./scripts/build_dashboard.sh "$DASHBOARD_NAME" 2>&1 | tail -1 || echo "   ⚠️  Build failed for $DASHBOARD_NAME"
        done <<< "$DASHBOARDS"
    fi
    
    # Generate docker-compose entries
    echo "   Generating docker-compose entries..."
    ./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml 2>&1 | tail -1 || echo "   ⚠️  Failed to generate docker-compose entries"
    
    # Setup dashboard nginx configurations
    # Dashboards are part of ScientistCloud 2.0, so we should set them up even if main services are skipped
    # New dashboards use separate .conf files in conf.d/ (different from old embedded configs)
    if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
        echo "   Setting up dashboard nginx configurations..."
        echo "   NOTE: New dashboards use separate .conf files in conf.d/ (automatically included by nginx)"
        echo "   Old dashboards are embedded in default.conf.https/default.conf.template"
        ./scripts/setup_dashboards_nginx.sh "$VISUS_DOCKER_PATH" 2>&1 | grep -E "(✅|⚠️|❌|Error)" || true
    else
        echo "   ⚠️  Skipping dashboard nginx setup (no VisusDataPortalPrivate path found)"
        echo "   To fix: Set VISUS_DOCKER or VISUS_CODE in env.scientistcloud file"
    fi
    
    popd
    echo "✅ Dashboard setup complete"
else
    echo "⚠️  SC_Dashboards directory not found: $DASHBOARDS_DIR"
    echo "   Skipping dashboard setup"
fi

echo "🎉 All services startup complete!"
echo ""
echo "Service URLs:"
echo "  🌐 Portal: https://scientistcloud.com/portal/"
if [ "$SKIP_MAIN_SERVICES" = false ]; then
    echo "  🏠 Main Site: https://scientistcloud.com/"
fi
echo "  🔧 Health: https://scientistcloud.com/portal/health"
if [ -d "$DASHBOARDS_DIR" ]; then
    echo ""
    echo "📊 Dashboard URLs:"
    DASHBOARDS=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | "\(.key):\(.value.nginx_path)"' "$DASHBOARDS_DIR/config/dashboard-registry.json" 2>/dev/null || echo "")
    if [ -n "$DASHBOARDS" ]; then
        while IFS=: read -r DASHBOARD_NAME NGINX_PATH; do
            echo "  📈 $DASHBOARD_NAME: https://scientistcloud.com${NGINX_PATH}"
        done <<< "$DASHBOARDS"
    fi
fi
echo ""
if [ "$SKIP_MAIN_SERVICES" = true ]; then
    echo "ℹ️  Note: Main VisusDataPortalPrivate services were skipped (portal-only mode)"
fi