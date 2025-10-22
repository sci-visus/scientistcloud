#!/bin/bash

# For ScientistCloud 2.0, we need to start all the services in the correct order

echo "🚀 Starting all ScientistCloud services..."

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

# Start main VisusDataPortalPrivate services
echo "🏠 Starting main VisusDataPortalPrivate services..."
if [ -d "~/VisStoreClone/visus-dataportal-private/Docker" ]; then
    pushd ~/VisStoreClone/visus-dataportal-private/Docker
    ./sync_with_github.sh
    ./scientistCloud_docker_start_fresh.sh
    ./setup_ssl.sh
    popd
    echo "✅ Main services started"
else
    echo "⚠️ VisusDataPortalPrivate Docker directory not found, skipping..."
fi

echo "🎉 All services startup complete!"
echo ""
echo "Service URLs:"
echo "  🌐 Portal: https://scientistcloud.com/portal/"
echo "  🏠 Main Site: https://scientistcloud.com/"
echo "  🔧 Health: https://scientistcloud.com/portal/health"