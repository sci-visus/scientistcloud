#!/bin/bash
 
# For ScientistCloud 2.0, we need to start all the services in the correct order
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

# Start main VisusDataPortalPrivate services
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
    exit 1
fi

# Setup portal nginx configuration after all services are running
echo "🔧 Setting up portal nginx configuration..."
if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
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
    echo "❌ Cannot setup portal nginx configuration - Docker directory not found"
    exit 1
fi

echo "🎉 All services startup complete!"
echo ""
echo "Service URLs:"
echo "  🌐 Portal: https://scientistcloud.com/portal/"
echo "  🏠 Main Site: https://scientistcloud.com/"
echo "  🔧 Health: https://scientistcloud.com/portal/health"