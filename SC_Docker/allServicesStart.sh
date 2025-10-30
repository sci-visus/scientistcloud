#!/bin/bash

# For ScientistCloud 2.0, we need to start all the services in the correct order

echo "🚀 Starting all ScientistCloud services..."

#Start Update SCLib_TryTest
echo "📦 Update SCLib_TryTest and copy env.scientistcloud to SCLib and SC Website..."
if [ -d "~/ScientistCloud2.0/SCLib_TryTest/" ]; then
    pushd ~/ScientistCloud2.0/SCLib_TryTest/
    git fetch origin
    git reset --hard origin/main
    cp env.scientistcloud ~/ScientistCloud2.0/scientistCloudLib/Docker/.env
    cp env.scientistcloud ~/ScientistCloud2.0/scientistcloud/SC_Docker/.env
    popd
    echo "✅ SCLib services started"
else
    echo "⚠️ SCLib Docker directory not found, skipping..."
fi


# Start SCLib services first
echo "📦 Starting SCLib services..."
if [ -d "~/ScientistCloud2.0/scientistCloudLib/Docker" ]; then
    pushd ~/ScientistCloud2.0/scientistCloudLib/Docker
    git fetch origin
    git reset --hard origin/main
    ./start.sh clean
    ./start.sh up
    popd
    echo "✅ SCLib services started"
else
    echo "⚠️ SCLib Docker directory not found, skipping..."
fi

# Start Portal services
echo "🌐 Starting Portal services..."
pushd ~/ScientistCloud2.0/scientistcloud/SC_Docker
git fetch origin
git reset --hard origin/main
./start.sh clean
./start.sh start
popd
echo "✅ Portal services started"

# Find VisusDataPortalPrivate Docker directory
# Try multiple common paths
VISUS_DOCKER_PATH=""
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

# If still not found, try to detect from running nginx container
if [ -z "$VISUS_DOCKER_PATH" ]; then
    # Try to find where nginx config is mounted from
    NGINX_CONF_PATH=$(docker inspect visstore_nginx 2>/dev/null | grep -o '"/[^"]*/nginx/conf\.d"' | head -1 | tr -d '"')
    if [ -n "$NGINX_CONF_PATH" ]; then
        # Extract the Docker directory path
        VISUS_DOCKER_PATH=$(dirname "$NGINX_CONF_PATH" 2>/dev/null || echo "")
    fi
fi

# Start main VisusDataPortalPrivate services
echo "🏠 Starting main VisusDataPortalPrivate services..."
if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
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
    echo "⚠️ VisusDataPortalPrivate Docker directory not found, skipping..."
    echo "   Searched in: ~/VisStoreClone, ~/VisStoreCode, ~/visus-dataportal-private"
fi

# Setup portal nginx configuration after all services are running
echo "🔧 Setting up portal nginx configuration..."
if [ -n "$VISUS_DOCKER_PATH" ] && [ -d "$VISUS_DOCKER_PATH" ]; then
    pushd "$VISUS_DOCKER_PATH"
    if [ -f "./setup_portal_nginx.sh" ]; then
        ./setup_portal_nginx.sh
        echo "✅ Portal nginx configuration updated"
    else
        echo "⚠️ setup_portal_nginx.sh not found, portal routes may not work"
        echo "   You can manually run the setup_portal_config function from setup_ssl.sh"
        # Try to run setup_portal_config if setup_ssl.sh exists
        if [ -f "./setup_ssl.sh" ]; then
            echo "   Attempting to add portal config via setup_ssl.sh..."
            # Source the function and call it
            source <(grep -A 76 "^setup_portal_config()" ./setup_ssl.sh)
            setup_portal_config 2>/dev/null || echo "   Failed to add portal config automatically"
        fi
    fi
    popd
else
    echo "⚠️ VisusDataPortalPrivate Docker directory not found, skipping portal config..."
    echo "   Please manually run: find ~ -name 'setup_portal_nginx.sh' -type f 2>/dev/null"
fi

echo "🎉 All services startup complete!"
echo ""
echo "Service URLs:"
echo "  🌐 Portal: https://scientistcloud.com/portal/"
echo "  🏠 Main Site: https://scientistcloud.com/"
echo "  🔧 Health: https://scientistcloud.com/portal/health"