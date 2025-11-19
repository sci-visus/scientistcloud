#!/bin/bash
 
# For ScientistCloud 2.0, we need to start all the services in the correct order
# Usage: ./allServicesStart.sh [OPTIONS]
#   --skip-main or --portal-only: Skip starting VisusDataPortalPrivate services
#   --dashboards-only or --only-dashboards: Only run dashboard setup (skip all other services)
#   -w or --web-only: Rebuild only SC_Web portal container (when SC_Web Dockerfile or dependencies change)
#   -s or --sclib-only: Rebuild only SCLib services (when SCLib code changes)
#   -sw or --sclib-web: Rebuild both SCLib and SC_Web (when both change)
#
# IMPORTANT NOTES - OPTIMIZATION GUIDE:
#   ✅ ALL CODE IS MOUNTED AS VOLUMES (no rebuild needed for code changes):
#      - SC_Web: Mounts ../SC_Web:/var/www/html (SC_Web code changes = just restart)
#      - SC_Web: Mounts ../../scientistCloudLib:/var/www/scientistCloudLib (SCLib code changes = just restart)
#      - SCLib FastAPI: Mounts ../:/app/scientistCloudLib (SCLib code changes = just restart)
#      - SCLib Auth: Mounts ../SCLib_Auth:/app (Auth code changes = just restart)
#
#   🔨 REBUILD ONLY WHEN:
#      - SCLib: Dockerfile changes (system packages, Python requirements.txt changes)
#      - SC_Web: Dockerfile changes (PHP dependencies, Apache config, system packages)
#      - Requirements files change (requirements.txt, composer.json with new packages)
#
#   ⚡ FOR CODE-ONLY CHANGES:
#      - Just restart containers: ./allServicesStart.sh (no flags = fastest)
#      - Or manually: docker restart sclib_fastapi scientistcloud-portal
#
#   📝 USAGE EXAMPLES:
#      ./allServicesStart.sh                    # Fast: Just restart (code changes only)
#      ./allServicesStart.sh -s                 # Rebuild SCLib (Dockerfile/requirements changed)
#      ./allServicesStart.sh -w                 # Rebuild SC_Web (Dockerfile/composer.json changed)
#      ./allServicesStart.sh -sw                # Rebuild both (both Dockerfiles changed)

# Parse command line arguments
SKIP_MAIN_SERVICES=false
DASHBOARDS_ONLY=false
REBUILD_WEB=false
REBUILD_SCLIB=false

for arg in "$@"; do
    case $arg in
        --skip-main|--portal-only)
            SKIP_MAIN_SERVICES=true
            echo "📋 Skipping VisusDataPortalPrivate services (portal-only mode)"
            ;;
        --dashboards-only|--only-dashboards)
            DASHBOARDS_ONLY=true
            SKIP_MAIN_SERVICES=true
            echo "📊 Running dashboards only (skipping all other services)"
            ;;
        -w|--web-only)
            REBUILD_WEB=true
            echo "🌐 Will rebuild SC_Web portal container"
            ;;
        -s|--sclib-only)
            REBUILD_SCLIB=true
            echo "📦 Will rebuild SCLib services"
            ;;
        -sw|--sclib-web|--both)
            REBUILD_WEB=true
            REBUILD_SCLIB=true
            echo "🔄 Will rebuild both SCLib and SC_Web containers"
            ;;
    esac
done

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

if [ "$DASHBOARDS_ONLY" = false ]; then
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
        echo "✅ Environment files copied (includes DOMAIN_NAME for dashboard containers)"
    else
        echo "⚠️ SCLib_TryTest directory not found: $SCLIB_TRYTEST_DIR"
    fi

    # Start SCLib services first
    echo "📦 Starting SCLib services..."
    SCLIB_DOCKER_DIR="$HOME/ScientistCloud2.0/scientistCloudLib/Docker"
    SCLIB_CODE_DIR="$HOME/ScientistCloud2.0/scientistCloudLib"
    
    # Pull latest code from scientistCloudLib repository (parent of Docker directory)
    if [ -d "$SCLIB_CODE_DIR" ]; then
        echo "   📥 Pulling latest SCLib code..."
        pushd "$SCLIB_CODE_DIR"
        git fetch origin
        git reset --hard origin/main
        popd
        echo "   ✅ SCLib code updated"
    fi
    
    if [ -d "$SCLIB_DOCKER_DIR" ]; then
        pushd "$SCLIB_DOCKER_DIR"
        git fetch origin
        git reset --hard origin/main
        
        if [ "$REBUILD_SCLIB" = true ]; then
            echo "   🔨 Rebuilding SCLib containers (code changes detected)..."
            # Clean containers, then rebuild and start
            # Note: start.sh up already does 'build --no-cache auth fastapi', ensuring fresh build with latest code
            ./start.sh clean
            ./start.sh up
            echo "✅ SCLib services rebuilt and started (FastAPI rebuilt with latest code)"
        else
            echo "   ⚡ Restarting SCLib services (code is mounted as volume, no rebuild needed)..."
            # Just restart - code is mounted as volume, so changes are already available
            ./start.sh restart || ./start.sh up
            echo "✅ SCLib services restarted (using mounted code volumes)"
        fi
        popd
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
        
        if [ "$REBUILD_WEB" = true ]; then
            echo "   🔨 Rebuilding SC_Web portal container (Dockerfile or dependencies changed)..."
            ./start.sh clean
            ./start.sh rebuild
            echo "✅ Portal services rebuilt and started"
        else
            echo "   ⚡ Restarting SC_Web portal (code is mounted as volume, no rebuild needed)..."
            # Just restart - both SC_Web and SCLib code are mounted as volumes
            ./start.sh restart || ./start.sh start
            echo "✅ Portal services restarted (using mounted code volumes)"
        fi
        popd
    else
        echo "❌ Portal Docker directory not found: $PORTAL_DOCKER_DIR"
        exit 1
    fi
else
    echo "📊 Dashboards-only mode: Skipping SCLib and Portal services"
    echo "   (Only running dashboard setup)"
fi

# Find VisusDataPortalPrivate Docker directory (needed for nginx configs even in dashboards-only mode)
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
            ./scientistCloud_docker_start_fresh.sh x
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
# Also set up in dashboards-only mode if portal container is already running
if [ "$DASHBOARDS_ONLY" = false ] || docker ps --format "{{.Names}}" | grep -q "scientistcloud-portal"; then
    if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
        echo "🔧 Setting up portal nginx configuration..."
        pushd "$VISUS_DOCKER_PATH"
        if [ -f "./setup_portal_nginx.sh" ]; then
            ./setup_portal_nginx.sh
            echo "✅ Portal nginx configuration updated"
        else
            echo "⚠️ setup_portal_nginx.sh not found"
            echo "   Portal routes may not work. Please ensure setup_portal_nginx.sh exists in $VISUS_DOCKER_PATH"
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
else
    echo "⏭️  Skipping portal nginx setup (portal container not running)"
fi

# Setup and build dashboards
# NOTE: New dashboards use separate .conf files in nginx/conf.d/ (automatically included)
# Old dashboards are embedded in default.conf.https/default.conf.template inside server blocks
# Ports are assigned to avoid conflicts with old dashboards (see PORT_CONFLICTS.md)
echo "📊 Setting up and building dashboards..."
# Find SC_Dashboards directory - try multiple possible locations
DASHBOARDS_DIR=""
if [ -d "$(pwd)/../SC_Dashboards" ]; then
    DASHBOARDS_DIR="$(cd "$(pwd)/../SC_Dashboards" && pwd)"
elif [ -d "$HOME/ScientistCloud2.0/scientistcloud/SC_Dashboards" ]; then
    DASHBOARDS_DIR="$HOME/ScientistCloud2.0/scientistcloud/SC_Dashboards"
elif [ -d "$HOME/ScientistCloud_2.0/scientistcloud/SC_Dashboards" ]; then
    DASHBOARDS_DIR="$HOME/ScientistCloud_2.0/scientistcloud/SC_Dashboards"
elif [ -d "$(dirname "$(dirname "$(dirname "$(pwd)")")")/scientistcloud/SC_Dashboards" ]; then
    DASHBOARDS_DIR="$(cd "$(dirname "$(dirname "$(dirname "$(pwd)")")")/scientistcloud/SC_Dashboards" && pwd)"
fi
if [ -d "$DASHBOARDS_DIR" ]; then
    pushd "$DASHBOARDS_DIR"
    
    # Regenerate registry from actual filenames to ensure keys match what user named them
    echo "   Regenerating dashboard registry from filenames..."
    if [ -f "./scripts/regenerate_registry.sh" ]; then
        ./scripts/regenerate_registry.sh 2>&1 | grep -E "(✅|⚠️|❌|Error|Registering)" || true
        echo "   ✅ Registry regenerated"
    else
        echo "   ⚠️  regenerate_registry.sh not found - using existing registry"
    fi
    
    # Export dashboard list (generates dashboards-list.json from registry)
    echo "   Exporting dashboard list..."
    if [ -f "./scripts/export_dashboard_list.sh" ]; then
        ./scripts/export_dashboard_list.sh 2>&1 | grep -E "(✅|⚠️|❌|Error|Total)" || true
    else
        echo "   ⚠️  export_dashboard_list.sh not found"
    fi
    
    # Initialize all enabled dashboards (generate Dockerfiles and nginx configs)
    # Regenerate to ensure latest fixes are applied (Dockerfiles and nginx configs)
    echo "   Initializing dashboards..."
    DASHBOARDS=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    if [ -n "$DASHBOARDS" ]; then
        while IFS= read -r DASHBOARD_NAME; do
            echo "   📦 Initializing $DASHBOARD_NAME..."
            # Force regeneration of Dockerfiles and nginx configs to apply latest fixes
            ./scripts/init_dashboard.sh "$DASHBOARD_NAME" --overwrite 2>&1 | grep -E "(✅|⚠️|❌|Error|Generated|Exported)" || true
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
    
    # Start dashboard containers using docker-compose
    if [ -f "../SC_Docker/dashboards-docker-compose.yml" ]; then
        echo "   Starting dashboard containers..."
        pushd ../SC_Docker
        
        # Ensure docker_visstore_web network exists (required for dashboards)
        if ! docker network inspect docker_visstore_web >/dev/null 2>&1; then
            echo "   Creating docker_visstore_web network..."
            docker network create docker_visstore_web || echo "   ⚠️  Network creation failed (may already exist)"
        fi
        
        # Remove old dashboard containers to avoid ContainerConfig errors
        echo "   Cleaning up old dashboard containers..."
        OLD_CONTAINERS=$(docker ps -a --filter "name=dashboard_" --format "{{.Names}}" 2>/dev/null || true)
        if [ -n "$OLD_CONTAINERS" ]; then
            echo "$OLD_CONTAINERS" | while read -r container; do
                if [ -n "$container" ]; then
                    echo "   🗑️  Removing old container: $container"
                    docker rm -f "$container" 2>/dev/null || true
                fi
            done
        fi
        
        # Find .env file - check SC_Docker first (where env.scientistcloud is copied), then VisusDataPortalPrivate
        # This ensures DOMAIN_NAME and other dashboard variables are available
        ENV_FILE=""
        if [ -f ".env" ]; then
            # SC_Docker/.env is created by copying env.scientistcloud (line 50)
            ENV_FILE=".env"
            echo "   Using .env file from SC_Docker: $ENV_FILE"
        elif [ -n "$VISUS_DOCKER_PATH" ] && [ -f "$VISUS_DOCKER_PATH/.env" ]; then
            ENV_FILE="$VISUS_DOCKER_PATH/.env"
            echo "   Using .env file from VisusDataPortalPrivate: $ENV_FILE"
        fi
        
        # Stop and remove any existing containers defined in docker-compose first
        echo "   Stopping existing dashboard containers..."
        docker-compose -f dashboards-docker-compose.yml down 2>/dev/null || true
        
        # Start containers
        if [ -n "$ENV_FILE" ]; then
            if docker-compose -f dashboards-docker-compose.yml --env-file "$ENV_FILE" up -d; then
                echo "   ✅ Dashboard containers started"
            else
                echo "   ❌ Failed to start dashboard containers"
                echo "   Checking container status..."
                docker-compose -f dashboards-docker-compose.yml ps || true
            fi
        else
            echo "   ⚠️  No .env file found - trying without explicit env-file"
            if docker-compose -f dashboards-docker-compose.yml up -d; then
                echo "   ✅ Dashboard containers started"
            else
                echo "   ❌ Failed to start dashboard containers"
                echo "   Checking container status..."
                docker-compose -f dashboards-docker-compose.yml ps || true
            fi
        fi
        
        # Verify containers are running
        echo "   Verifying dashboard containers..."
        RUNNING_CONTAINERS=$(docker-compose -f dashboards-docker-compose.yml ps --services --filter "status=running" 2>/dev/null | wc -l)
        TOTAL_CONTAINERS=$(docker-compose -f dashboards-docker-compose.yml ps --services 2>/dev/null | wc -l)
        if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
            echo "   ✅ $RUNNING_CONTAINERS/$TOTAL_CONTAINERS dashboard containers running"
            docker-compose -f dashboards-docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
        else
            echo "   ⚠️  No dashboard containers running - checking status..."
            docker-compose -f dashboards-docker-compose.yml ps 2>/dev/null || true
        fi
        
        popd
    else
        echo "   ⚠️  dashboards-docker-compose.yml not found - skipping container startup"
    fi
    
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
    
    # Final nginx reload to ensure all configs are applied (portal + dashboards)
    if [ -n "$VISUS_DOCKER_PATH" ] && docker ps --format "{{.Names}}" | grep -q "visstore_nginx"; then
        echo "🔄 Performing final nginx reload to apply all configuration changes..."
        if docker exec visstore_nginx nginx -t >/dev/null 2>&1; then
            docker exec visstore_nginx nginx -s reload
            echo "✅ Nginx reloaded with all configuration changes"
        else
            echo "⚠️  Nginx configuration test failed - skipping reload"
            echo "   Check nginx logs: docker logs visstore_nginx"
        fi
    fi
else
    echo "⚠️  SC_Dashboards directory not found: $DASHBOARDS_DIR"
    echo "   Skipping dashboard setup"
fi

if [ "$DASHBOARDS_ONLY" = true ]; then
    echo "🎉 Dashboard setup complete!"
else
    echo "🎉 All services startup complete!"
    echo ""
    echo "Service URLs:"
    echo "  🌐 Portal: https://scientistcloud.com/portal/"
    if [ "$SKIP_MAIN_SERVICES" = false ]; then
        echo "  🏠 Main Site: https://scientistcloud.com/"
    fi
    echo "  🔧 Health: https://scientistcloud.com/portal/health"
fi

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

if [ "$DASHBOARDS_ONLY" = false ]; then
    echo ""
    if [ "$SKIP_MAIN_SERVICES" = true ]; then
        echo "ℹ️  Note: Main VisusDataPortalPrivate services were skipped (portal-only mode)"
    fi
    
    # Show rebuild summary
    if [ "$REBUILD_WEB" = true ] || [ "$REBUILD_SCLIB" = true ]; then
        echo ""
        echo "🔨 Rebuild Summary:"
        if [ "$REBUILD_WEB" = true ]; then
            echo "   ✅ SC_Web portal container was rebuilt"
        fi
        if [ "$REBUILD_SCLIB" = true ]; then
            echo "   ✅ SCLib services were rebuilt"
        fi
    else
        echo ""
        echo "⚡ Optimization: No rebuilds performed (code is mounted as volumes)"
        echo "   💡 Code changes are available immediately - containers were restarted"
        echo "   💡 Use -s, -w, or -sw flags only when Dockerfiles or requirements change"
    fi
fi