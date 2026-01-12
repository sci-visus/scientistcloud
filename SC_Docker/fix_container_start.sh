#!/bin/bash
# Fix docker-compose ContainerConfig error and restart portal

set -e

echo "🔧 Fixing Container Start Issue"
echo "================================"
echo ""

# Stop and remove the existing container
echo "1️⃣ Stopping and removing existing container..."
docker stop scientistcloud-portal 2>/dev/null || true
docker rm scientistcloud-portal 2>/dev/null || true
echo "✅ Container removed"
echo ""

# Start using docker-compose (should work now)
echo "2️⃣ Starting container with docker-compose..."
docker-compose up -d scientistcloud-portal
echo "✅ Container started"
echo ""

# Wait for it to be ready
echo "3️⃣ Waiting for container to be ready (5 seconds)..."
sleep 5

# Check if it's running
if docker ps | grep -q scientistcloud-portal; then
    echo "✅ Container is running!"
    echo ""
    echo "4️⃣ Checking container status..."
    docker ps | grep scientistcloud-portal
    echo ""
    echo "5️⃣ Testing dashboards API..."
    sleep 3
    curl -s https://scientistcloud.com/portal/api/dashboards.php | head -50
else
    echo "❌ Container failed to start. Checking logs..."
    docker logs scientistcloud-portal --tail 50
fi

