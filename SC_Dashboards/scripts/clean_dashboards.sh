#!/bin/bash
# Clean dashboard Docker containers and images
# Usage: ./clean_dashboards.sh [OPTIONS]
#   --containers-only: Only remove containers, keep images
#   --images-only: Only remove images, keep containers
#   --all: Remove containers, images, and volumes (default)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_COMPOSE_FILE="$SCRIPT_DIR/../../SC_Docker/dashboards-docker-compose.yml"

CONTAINERS_ONLY=false
IMAGES_ONLY=false
REMOVE_ALL=true

# Parse arguments
for arg in "$@"; do
    case $arg in
        --containers-only)
            CONTAINERS_ONLY=true
            REMOVE_ALL=false
            ;;
        --images-only)
            IMAGES_ONLY=true
            REMOVE_ALL=false
            ;;
        --all)
            REMOVE_ALL=true
            ;;
    esac
done

echo "🧹 Cleaning dashboard Docker resources..."

# Change to SC_Docker directory if docker-compose file exists
if [ -f "$DOCKER_COMPOSE_FILE" ]; then
    pushd "$(dirname "$DOCKER_COMPOSE_FILE")" >/dev/null
    
    # Stop and remove containers using docker-compose
    if [ "$REMOVE_ALL" = true ] || [ "$CONTAINERS_ONLY" = true ]; then
        echo "   Stopping and removing dashboard containers..."
        docker-compose -f dashboards-docker-compose.yml down 2>/dev/null || true
        
        # Also remove any orphaned dashboard containers
        echo "   Removing orphaned dashboard containers..."
        docker ps -a --filter "name=dashboard_" --format "{{.Names}}" | while read -r container; do
            if [ -n "$container" ]; then
                echo "   🗑️  Removing: $container"
                docker rm -f "$container" 2>/dev/null || true
            fi
        done
    fi
    
    # Remove images
    if [ "$REMOVE_ALL" = true ] || [ "$IMAGES_ONLY" = true ]; then
        echo "   Removing dashboard images..."
        # Get image names from docker-compose
        if [ -f "dashboards-docker-compose.yml" ]; then
            docker-compose -f dashboards-docker-compose.yml config --images 2>/dev/null | while read -r image; do
                if [ -n "$image" ] && [ "$image" != "null" ]; then
                    echo "   🗑️  Removing image: $image"
                    docker rmi -f "$image" 2>/dev/null || true
                fi
            done
        fi
        
        # Also try to remove by common dashboard image patterns
        echo "   Removing dashboard images by pattern..."
        for pattern in "3dplotly" "3dvtk" "4d_dashboard" "magicscan" "openvisusslice"; do
            docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "$pattern" | while read -r image; do
                if [ -n "$image" ]; then
                    echo "   🗑️  Removing image: $image"
                    docker rmi -f "$image" 2>/dev/null || true
                fi
            done
        done
    fi
    
    popd >/dev/null
else
    echo "⚠️  docker-compose file not found: $DOCKER_COMPOSE_FILE"
    echo "   Cleaning up manually..."
    
    # Manual cleanup
    if [ "$REMOVE_ALL" = true ] || [ "$CONTAINERS_ONLY" = true ]; then
        echo "   Removing dashboard containers..."
        docker ps -a --filter "name=dashboard_" --format "{{.Names}}" | while read -r container; do
            if [ -n "$container" ]; then
                echo "   🗑️  Removing: $container"
                docker rm -f "$container" 2>/dev/null || true
            fi
        done
    fi
    
    if [ "$REMOVE_ALL" = true ] || [ "$IMAGES_ONLY" = true ]; then
        echo "   Removing dashboard images..."
        for pattern in "3dplotly" "3dvtk" "4d_dashboard" "magicscan" "openvisusslice"; do
            docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "$pattern" | while read -r image; do
                if [ -n "$image" ]; then
                    echo "   🗑️  Removing image: $image"
                    docker rmi -f "$image" 2>/dev/null || true
                fi
            done
        done
    fi
fi

echo "✅ Dashboard cleanup complete!"
echo ""
echo "To rebuild and start dashboards, run:"
echo "   cd ~/ScientistCloud2.0/scientistcloud/SC_Dashboards"
echo "   # Or: cd ~/ScientistCloud2.0/scientistcloud/SC_Docker"
echo "   ./allServicesStart.sh --dashboards-only"

