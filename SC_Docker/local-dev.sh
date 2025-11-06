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
    print_status "Starting dashboard container: $container_name on port $port"
    docker run -d \
        --name "$container_name" \
        --network docker_visstore_web \
        -p "$port:$port" \
        -e DOMAIN_NAME="${DOMAIN_NAME:-localhost}" \
        -e DEPLOY_SERVER="${DEPLOY_SERVER:-http://localhost}" \
        -e SECRET_KEY="${SECRET_KEY:-local-dev-secret}" \
        -e DB_NAME="${DB_NAME:-scientistcloud}" \
        -e MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}" \
        "${dashboard_lower}_dashboard:latest" || {
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

# Function to start all dashboards
start_all_dashboards() {
    print_status "Starting all dashboards..."
    
    # Get list of enabled dashboards
    local dashboards_list="../SC_Dashboards/config/dashboards-list.json"
    if [ ! -f "$dashboards_list" ]; then
        print_error "Dashboards list not found: $dashboards_list"
        return 1
    fi
    
    # Extract dashboard IDs
    local dashboards=$(jq -r '.dashboards[] | select(.enabled == true) | .id' "$dashboards_list" 2>/dev/null)
    
    if [ -z "$dashboards" ]; then
        print_warning "No enabled dashboards found"
        return 0
    fi
    
    for dashboard in $dashboards; do
        start_dashboard "$dashboard" || print_warning "Failed to start $dashboard"
    done
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
    
    # Stop all dashboard containers
    docker ps --format "{{.Names}}" | grep "^dashboard_" | while read container; do
        print_status "Stopping $container..."
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    done
    
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

