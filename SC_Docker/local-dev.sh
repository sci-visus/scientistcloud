#!/bin/bash

# Local Development Setup for ScientistCloud Portal and Dashboards
# This script sets up a local development environment for testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env.local exists, create from template if not
if [ ! -f ".env.local" ]; then
    print_status "Creating .env.local from template..."
    if [ -f ".env" ]; then
        cp .env .env.local
        print_warning "Created .env.local - please update DOMAIN_NAME to 'localhost' for local testing"
    else
        print_error ".env file not found. Please create .env.local manually."
        exit 1
    fi
fi

# Source local environment
if [ -f ".env.local" ]; then
    print_status "Loading local environment variables..."
    set -o allexport
    source .env.local
    set +o allexport
    
    # Override for local development
    export DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
    export DEPLOY_SERVER="${DEPLOY_SERVER:-http://localhost}"
    print_success "Environment loaded (DOMAIN_NAME=$DOMAIN_NAME)"
fi

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to start portal
start_portal() {
    print_status "Starting Portal on port 8080..."
    
    if check_port 8080; then
        print_warning "Port 8080 is already in use. Stopping existing container..."
        docker-compose -f docker-compose.yml down 2>/dev/null || true
        sleep 2
    fi
    
    # Build and start portal
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.yml up -d scientistcloud-portal
    
    # Wait for portal to be ready
    print_status "Waiting for portal to be ready..."
    for i in {1..30}; do
        if curl -f http://localhost:8080/test-simple.php &> /dev/null; then
            print_success "Portal is ready at http://localhost:8080"
            return 0
        fi
        sleep 1
    done
    
    print_error "Portal failed to start"
    docker-compose -f docker-compose.yml logs scientistcloud-portal
    return 1
}

# Function to check if base image exists
check_base_image() {
    local base_image="$1"
    if docker image inspect "$base_image" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to get required base image for a dashboard
get_dashboard_base_image() {
    local config_file="$1"
    local base_image=$(jq -r '.base_image // empty' "$config_file" 2>/dev/null)
    local base_image_tag=$(jq -r '.base_image_tag // "latest"' "$config_file" 2>/dev/null)
    
    if [ -n "$base_image" ] && [ "$base_image" != "null" ]; then
        echo "${base_image}:${base_image_tag}"
    else
        echo ""
    fi
}

# Function to start a single dashboard
start_dashboard() {
    local dashboard_name=$1
    local dashboard_lower=$(echo "$dashboard_name" | tr '[:upper:]' '[:lower:]')
    
    print_status "Starting dashboard: $dashboard_name"
    
    # Get dashboard config
    local config_file="../SC_Dashboards/dashboards/${dashboard_name}.json"
    if [ ! -f "$config_file" ]; then
        # Try alternative naming
        config_file="../SC_Dashboards/dashboards/${dashboard_lower}.json"
    fi
    
    if [ ! -f "$config_file" ]; then
        print_error "Dashboard config not found: $dashboard_name"
        return 1
    fi
    
    # Check for required base image
    local required_base=$(get_dashboard_base_image "$config_file")
    if [ -n "$required_base" ]; then
        if ! check_base_image "$required_base"; then
            print_error "Required base image not found: $required_base"
            print_warning "Base images need to be built from VisusDataPortalPrivate/Docker/"
            print_warning "You can either:"
            print_warning "  1. Build base images manually (see VisusDataPortalPrivate/Docker/rebuild-base-images.sh)"
            print_warning "  2. Skip dashboard building with: ./local-dev.sh start --skip-dashboards"
            print_warning "  3. Build base images from the other repository first"
            return 1
        else
            print_success "Base image found: $required_base"
        fi
    fi
    
    # Extract port from config
    local port=$(jq -r '.port' "$config_file" 2>/dev/null)
    if [ -z "$port" ] || [ "$port" = "null" ]; then
        print_error "Could not determine port for $dashboard_name"
        return 1
    fi
    
    # Check if port is in use
    if check_port $port; then
        print_warning "Port $port is already in use. Dashboard may already be running."
        return 0
    fi
    
    # Build dashboard if needed
    print_status "Building dashboard: $dashboard_name"
    cd ../SC_Dashboards
    ./scripts/build_dashboard.sh "$dashboard_name" || {
        print_error "Failed to build dashboard: $dashboard_name"
        cd "$SCRIPT_DIR"
        return 1
    }
    cd "$SCRIPT_DIR"
    
    # Get container name
    local container_name="dashboard_${dashboard_lower}"
    
    # Stop existing container if running
    docker stop "$container_name" 2>/dev/null || true
    docker rm "$container_name" 2>/dev/null || true
    
    # Run dashboard container
    # Image name matches what build_dashboard.sh creates (e.g., 3dplotly:latest, not 3dplotly_dashboard:latest)
    local image_name="${dashboard_lower}:latest"
    print_status "Starting dashboard container: $container_name on port $port (image: $image_name)"
    docker run -d \
        --name "$container_name" \
        --network docker_visstore_web \
        -p "$port:$port" \
        -e DOMAIN_NAME="${DOMAIN_NAME:-localhost}" \
        -e DEPLOY_SERVER="${DEPLOY_SERVER:-http://localhost}" \
        -e SECRET_KEY="${SECRET_KEY:-local-dev-secret}" \
        -e DB_NAME="${DB_NAME:-scientistcloud}" \
        -e MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}" \
        "$image_name" || {
        print_error "Failed to start dashboard container"
        return 1
    }
    
    # Wait for dashboard to be ready
    print_status "Waiting for dashboard to be ready..."
    sleep 5
    
    # Check health
    local health_path=$(jq -r '.health_check_path // "/health"' "$config_file" 2>/dev/null)
    for i in {1..20}; do
        if curl -f "http://localhost:$port$health_path" &> /dev/null 2>&1; then
            print_success "Dashboard $dashboard_name is ready at http://localhost:$port"
            return 0
        fi
        sleep 1
    done
    
    print_warning "Dashboard $dashboard_name may not be fully ready (check logs with: docker logs $container_name)"
    return 0
}

# Function to start all dashboards using docker-compose (matches allServicesStart.sh)
start_all_dashboards() {
    print_status "Setting up and building dashboards..."
    
    # Find SC_Dashboards directory (same logic as allServicesStart.sh)
    local dashboards_dir=""
    if [ -d "$(pwd)/../SC_Dashboards" ]; then
        dashboards_dir="$(cd "$(pwd)/../SC_Dashboards" && pwd)"
    elif [ -d "$HOME/ScientistCloud2.0/scientistcloud/SC_Dashboards" ]; then
        dashboards_dir="$HOME/ScientistCloud2.0/scientistcloud/SC_Dashboards"
    elif [ -d "$HOME/ScientistCloud_2.0/scientistcloud/SC_Dashboards" ]; then
        dashboards_dir="$HOME/ScientistCloud_2.0/scientistcloud/SC_Dashboards"
    fi
    
    if [ ! -d "$dashboards_dir" ]; then
        print_error "SC_Dashboards directory not found"
        return 1
    fi
    
    pushd "$dashboards_dir"
    
    # Initialize all enabled dashboards (generate Dockerfiles and nginx configs)
    # Regenerate to ensure latest fixes are applied (matches allServicesStart.sh)
    print_status "Initializing dashboards..."
    local dashboards=$(jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' config/dashboard-registry.json 2>/dev/null || echo "")
    if [ -n "$dashboards" ]; then
        while IFS= read -r dashboard_name; do
            print_status "📦 Initializing $dashboard_name..."
            # Force regeneration of Dockerfiles and nginx configs to apply latest fixes
            ./scripts/init_dashboard.sh "$dashboard_name" --overwrite 2>&1 | grep -E "(✅|⚠️|❌|Error|Generated|Exported)" || true
        done <<< "$dashboards"
    fi
    
    # Build all enabled dashboards (matches allServicesStart.sh)
    print_status "Building dashboard Docker images..."
    if [ -n "$dashboards" ]; then
        while IFS= read -r dashboard_name; do
            print_status "🐳 Building $dashboard_name..."
            ./scripts/build_dashboard.sh "$dashboard_name" 2>&1 | tail -1 || print_warning "Build failed for $dashboard_name"
        done <<< "$dashboards"
    fi
    
    # Generate docker-compose entries (matches allServicesStart.sh)
    print_status "Generating docker-compose entries..."
    ./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml 2>&1 | tail -1 || print_warning "Failed to generate docker-compose entries"
    
    # Start dashboard containers using docker-compose (matches allServicesStart.sh)
    if [ -f "../SC_Docker/dashboards-docker-compose.yml" ]; then
        print_status "Starting dashboard containers..."
        pushd ../SC_Docker
        
        # Ensure docker_visstore_web network exists (required for dashboards)
        if ! docker network inspect docker_visstore_web >/dev/null 2>&1; then
            print_status "Creating docker_visstore_web network..."
            docker network create docker_visstore_web || print_warning "Network creation failed (may already exist)"
        fi
        
        # Remove old dashboard containers to avoid ContainerConfig errors
        print_status "Cleaning up old dashboard containers..."
        local old_containers=$(docker ps -a --filter "name=dashboard_" --format "{{.Names}}" 2>/dev/null || true)
        if [ -n "$old_containers" ]; then
            echo "$old_containers" | while read -r container; do
                if [ -n "$container" ]; then
                    print_status "🗑️  Removing old container: $container"
                    docker rm -f "$container" 2>/dev/null || true
                fi
            done
        fi
        
        # Find .env file - check .env.local first (for local dev), then .env
        local env_file=""
        if [ -f ".env.local" ]; then
            env_file=".env.local"
            print_status "Using .env.local file: $env_file"
        elif [ -f ".env" ]; then
            env_file=".env"
            print_status "Using .env file: $env_file"
        fi
        
        # Stop and remove any existing containers defined in docker-compose first
        print_status "Stopping existing dashboard containers..."
        docker-compose -f dashboards-docker-compose.yml down 2>/dev/null || true
        
        # Start containers (matches allServicesStart.sh)
        if [ -n "$env_file" ]; then
            if docker-compose -f dashboards-docker-compose.yml --env-file "$env_file" up -d; then
                print_success "Dashboard containers started"
            else
                print_error "Failed to start dashboard containers"
                print_status "Checking container status..."
                docker-compose -f dashboards-docker-compose.yml ps || true
            fi
        else
            print_warning "No .env file found - trying without explicit env-file"
            if docker-compose -f dashboards-docker-compose.yml up -d; then
                print_success "Dashboard containers started"
            else
                print_error "Failed to start dashboard containers"
                print_status "Checking container status..."
                docker-compose -f dashboards-docker-compose.yml ps || true
            fi
        fi
        
        # Verify containers are running (matches allServicesStart.sh)
        print_status "Verifying dashboard containers..."
        local running_containers=$(docker-compose -f dashboards-docker-compose.yml ps --services --filter "status=running" 2>/dev/null | wc -l)
        local total_containers=$(docker-compose -f dashboards-docker-compose.yml ps --services 2>/dev/null | wc -l)
        if [ "$running_containers" -gt 0 ]; then
            print_success "$running_containers/$total_containers dashboard containers running"
            docker-compose -f dashboards-docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
        else
            print_warning "No dashboard containers running - checking status..."
            docker-compose -f dashboards-docker-compose.yml ps 2>/dev/null || true
        fi
        
        popd
    else
        print_error "dashboards-docker-compose.yml not found after generation"
    fi
    
    popd
}

# Function to create local nginx config (optional)
setup_local_nginx() {
    print_status "Setting up local nginx configuration..."
    
    local nginx_conf="nginx/local-dev.conf"
    mkdir -p nginx
    
    cat > "$nginx_conf" <<EOF
# Local Development Nginx Configuration
# Access portal at http://localhost:8080
# Access dashboards at http://localhost:<port>

server {
    listen 8080;
    server_name localhost;

    # Portal
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    
    # Dashboard routes (direct port access for local dev)
    location /dashboard/plotly/ {
        proxy_pass http://localhost:8060/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /dashboard/vtk/ {
        proxy_pass http://localhost:8051/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /dashboard/4d/ {
        proxy_pass http://localhost:8052/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /dashboard/magicscan/ {
        proxy_pass http://localhost:8053/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /dashboard/openvisusslice/ {
        proxy_pass http://localhost:8054/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    print_success "Local nginx config created at $nginx_conf"
    print_warning "For local dev, you can access dashboards directly at http://localhost:<port>"
}

# Function to show status
show_status() {
    echo ""
    print_success "Local Development Environment Status"
    echo "=========================================="
    echo ""
    
    # Portal status
    if docker ps --format "{{.Names}}" | grep -q "scientistcloud-portal"; then
        print_success "✅ Portal: http://localhost:8080"
    else
        print_error "❌ Portal: Not running"
    fi
    
    echo ""
    echo "Dashboards:"
    
    # Check each dashboard
    local dashboards_list="../SC_Dashboards/config/dashboards-list.json"
    if [ -f "$dashboards_list" ]; then
        local dashboards=$(jq -r '.dashboards[] | select(.enabled == true) | "\(.id)|\(.port)|\(.nginx_path)"' "$dashboards_list" 2>/dev/null)
        
        while IFS='|' read -r id port path; do
            local container_name="dashboard_$(echo "$id" | tr '[:upper:]' '[:lower:]')"
            if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
                print_success "  ✅ $id: http://localhost:$port (path: $path)"
            else
                print_error "  ❌ $id: Not running"
            fi
        done <<< "$dashboards"
    fi
    
    echo ""
    echo "Useful Commands:"
    echo "  View portal logs: docker logs -f scientistcloud-portal"
    echo "  View dashboard logs: docker logs -f dashboard_<name>"
    echo "  Stop all: ./local-dev.sh stop"
    echo "  Restart: ./local-dev.sh restart"
    echo ""
}

# Function to stop all services
stop_all() {
    print_status "Stopping all local development services..."
    
    # Stop portal
    docker-compose -f docker-compose.yml down 2>/dev/null || true
    
    # Stop dashboard containers using docker-compose if file exists
    if [ -f "dashboards-docker-compose.yml" ]; then
        print_status "Stopping dashboard containers with docker-compose..."
        docker-compose -f dashboards-docker-compose.yml down 2>/dev/null || true
    else
        # Fallback to individual container stop
        docker ps --format "{{.Names}}" | grep "^dashboard_" | while read container; do
            print_status "Stopping $container..."
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        done
    fi
    
    print_success "All services stopped"
}

# Main command handling
case "${1:-start}" in
    "start")
        print_status "Starting local development environment..."
        
        # Create docker network if it doesn't exist
        docker network create docker_visstore_web 2>/dev/null || true
        
        start_portal
        start_all_dashboards
        show_status
        ;;
    "portal")
        start_portal
        show_status
        ;;
    "dashboards")
        start_all_dashboards
        show_status
        ;;
    "dashboard")
        if [ -z "$2" ]; then
            print_error "Please specify dashboard name: ./local-dev.sh dashboard <name>"
            exit 1
        fi
        start_dashboard "$2"
        show_status
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        stop_all
        sleep 2
        ./local-dev.sh start
        ;;
    "status")
        show_status
        ;;
    "logs")
        if [ -z "$2" ]; then
            print_error "Please specify service: ./local-dev.sh logs <portal|dashboard_name>"
            exit 1
        fi
        if [ "$2" = "portal" ]; then
            docker logs -f scientistcloud-portal
        else
            docker logs -f "dashboard_$(echo "$2" | tr '[:upper:]' '[:lower:]')"
        fi
        ;;
    "nginx")
        setup_local_nginx
        ;;
    "help")
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  start       - Start portal and all dashboards (default)"
        echo "  portal      - Start only the portal"
        echo "  dashboards  - Start all dashboards"
        echo "  dashboard <name> - Start a specific dashboard"
        echo "  stop        - Stop all services"
        echo "  restart     - Restart all services"
        echo "  status      - Show status of all services"
        echo "  logs <name> - View logs (portal or dashboard name)"
        echo "  nginx       - Generate local nginx config"
        echo "  help        - Show this help"
        echo ""
        echo "Examples:"
        echo "  ./local-dev.sh start"
        echo "  ./local-dev.sh dashboard 3DPlotly"
        echo "  ./local-dev.sh logs portal"
        echo "  ./local-dev.sh logs 3dplotly"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac

