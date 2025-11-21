#!/bin/bash

# ScientistCloud Data Portal - Unified Deployment Script
# Integrates with both VisusDataPortalPrivate and scientistCloudLib systems

set -e  # Exit on any error

echo "🚀 ScientistCloud Data Portal - Unified Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check existing systems
check_existing_systems() {
    print_status "Checking existing ScientistCloud systems..."
    
    # Check VisusDataPortalPrivate system
    if docker ps --format "table {{.Names}}" | grep -q "visstore"; then
        print_success "Found VisusDataPortalPrivate containers"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "visstore"
    else
        print_warning "VisusDataPortalPrivate containers not found"
        print_warning "Make sure your existing system is running first"
    fi
    
    # Check scientistCloudLib system
    if docker ps --format "table {{.Names}}" | grep -q "sclib"; then
        print_success "Found scientistCloudLib containers"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "sclib"
    else
        print_warning "scientistCloudLib containers not found"
        print_warning "Make sure your SCLib system is running first"
    fi
}

# Integrate with existing nginx
integrate_nginx() {
    print_status "Integrating with existing nginx setup..."
    
    # Check if VisusDataPortalPrivate nginx directory exists
    VISUS_NGINX_PATH="/home/amy/VisStoreClone/visus-dataportal-private/Docker/nginx/conf.d"
    PORTAL_NGINX_PATH="./nginx/portal.conf"
    
    if [ ! -d "$VISUS_NGINX_PATH" ]; then
        print_warning "VisusDataPortalPrivate nginx directory not found: $VISUS_NGINX_PATH"
        print_warning "Portal will be accessible directly at http://localhost:8080"
        return
    fi
    
    if [ ! -f "$PORTAL_NGINX_PATH" ]; then
        print_warning "Portal nginx configuration not found: $PORTAL_NGINX_PATH"
        print_warning "Portal will be accessible directly at http://localhost:8080"
        return
    fi
    
    # Remove any existing problematic portal.conf file
    print_status "Removing any existing problematic portal configuration..."
    docker exec visstore_nginx rm -f /etc/nginx/conf.d/portal.conf 2>/dev/null || true
    
    print_success "Portal configuration cleanup completed"
    print_warning "Portal will be accessible directly at http://127.0.0.1:8080"
    print_warning "For nginx integration, use the setup_ssl.sh script which embeds the configuration properly"
}

# Check if .env file exists
check_env() {
    print_status "Checking environment configuration..."
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f "env.template" ]; then
            cp env.template .env
            print_warning "Please edit .env file with your actual values before continuing."
            print_warning "Press Enter to continue after editing .env file..."
            read
        else
            print_error "env.template file not found. Cannot create .env file."
            exit 1
        fi
    fi
    print_success "Environment configuration found"
}

# Check SCLib integration
check_sclib() {
    print_status "Checking SCLib integration..."
    
    # Check if SCLib directory exists
    if [ ! -d "../../scientistCloudLib" ]; then
        print_warning "SCLib directory not found at ../../scientistCloudLib"
        print_warning "SCLib files will not be available in the container"
    else
        print_success "SCLib directory found"
        
        # Check for key SCLib files
        if [ -f "../../scientistCloudLib/SCLib_JobProcessing/SCLib_Config.php" ]; then
            print_success "SCLib_Config.php found"
        else
            print_warning "SCLib_Config.php not found - SCLib integration may not work"
        fi
    fi
}

# Check if SSL certificates exist
check_ssl() {
    print_status "Checking SSL certificates..."
    
    # Check if VisusDataPortalPrivate has SSL certificates
    VISUS_SSL_PATH="/home/amy/VisStoreClone/visus-dataportal-private/Docker/certbot/conf"
    if [ -d "$VISUS_SSL_PATH" ] && [ -f "$VISUS_SSL_PATH/live/scientistcloud.com/fullchain.pem" ]; then
        print_success "Found existing SSL certificates in VisusDataPortalPrivate"
        print_success "Portal will use existing SSL certificates via visstore_nginx"
    else
        print_warning "SSL certificates not found in VisusDataPortalPrivate"
        print_warning "Portal will be accessible via HTTP only"
        print_warning "Please ensure your VisusDataPortalPrivate system has SSL configured"
    fi
}

# Build containers
build_containers() {
    print_status "Building portal containers..."
    docker-compose build --no-cache
    print_success "Portal containers built successfully"
}

# Start services
start_services() {
    print_status "Starting portal services..."
    docker-compose up -d
    print_success "Portal services started"
}

# Install PHP dependencies in container
install_dependencies() {
    print_status "Installing PHP dependencies in portal container..."
    
    # Wait for container to be fully started
    sleep 5
    
    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "scientistcloud-portal"; then
        print_warning "Portal container not found, skipping dependency installation"
        return
    fi
    
    # Install/update dependencies
    print_status "Running composer update..."
    if docker exec scientistcloud-portal bash -c "cd /var/www/html && composer update --no-dev --optimize-autoloader --no-interaction --prefer-dist 2>&1"; then
        print_success "Dependencies updated successfully"
    else
        print_warning "Composer update failed, trying install..."
        if docker exec scientistcloud-portal bash -c "cd /var/www/html && composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist 2>&1"; then
            print_success "Dependencies installed successfully"
        else
            print_warning "Composer install also failed - dependencies may be missing"
        fi
    fi
    
    # Regenerate autoloader
    print_status "Regenerating autoloader..."
    if docker exec scientistcloud-portal bash -c "cd /var/www/html && composer dump-autoload --optimize --no-interaction 2>&1"; then
        print_success "Autoloader regenerated"
    else
        print_warning "Autoloader regeneration failed"
    fi
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Install dependencies after container starts
    install_dependencies
    
    # Check if portal is responding
    for i in {1..30}; do
        if curl -f http://127.0.0.1:8080/test-simple.php &> /dev/null; then
            print_success "Portal is responding"
            break
        fi
        print_status "Waiting for portal... ($i/30)"
        sleep 2
    done
}

# Check service health
check_health() {
    print_status "Checking service health..."
    
    # Check container status
    if docker-compose ps | grep -q "Up"; then
        print_success "Portal containers are running"
    else
        print_error "Some portal containers are not running"
        docker-compose ps
        exit 1
    fi
    
    # Check portal health
    if curl -f http://127.0.0.1:8080/test-simple.php &> /dev/null; then
        print_success "Portal health check passed"
    else
        print_error "Portal health check failed"
        exit 1
    fi
}

# Test integration
test_integration() {
    print_status "Testing integration with existing systems..."
    
    # Test Portal configuration
    if curl -f http://127.0.0.1:8080/test-config.php &> /dev/null; then
        print_success "Portal configuration test accessible"
    else
        print_warning "Portal configuration test may not be accessible"
    fi
    
    # Test SCLib API connection
    if curl -f http://127.0.0.1:8080/test-sclib-api.php &> /dev/null; then
        print_success "Portal can connect to SCLib API"
    else
        print_warning "Portal may not be able to connect to SCLib API"
    fi
    
    # Test VisusDataPortalPrivate system connection
    if curl -f http://localhost:3000 &> /dev/null; then
        print_success "VisusDataPortalPrivate system is accessible"
    else
        print_warning "VisusDataPortalPrivate system may not be accessible"
    fi
    
    # Test scientistCloudLib system connection
    if curl -f http://localhost:5001 &> /dev/null; then
        print_success "scientistCloudLib API is accessible"
    else
        print_warning "scientistCloudLib API may not be accessible"
    fi
    
    # Test Auth service
    if curl -f http://localhost:8001 &> /dev/null; then
        print_success "Auth service is accessible"
    else
        print_warning "Auth service may not be accessible"
    fi
}

# Display access information
show_access_info() {
    echo ""
    echo "🎉 Unified Integration Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Portal Access URLs:"
    echo "  📱 Portal: https://scientistcloud.com/portal"
    echo "  🔧 Health: https://scientistcloud.com/portal/health"
    echo "  📱 Direct: http://127.0.0.1:8080/test-index.php"
    echo ""
    echo "Existing System URLs:"
    echo "  🏠 VisusDataPortalPrivate: http://localhost:3000"
    echo "  🔌 scientistCloudLib API: http://localhost:5001"
    echo "  🔐 Auth Service: http://localhost:8001"
    echo "  📊 Plotly: http://localhost:8050"
    echo "  📈 Bokeh: http://localhost:5006"
    echo "  🎯 Bokeh Dashboard: http://localhost:5008"
    echo "  ♟️ Chess Dashboard: http://localhost:5009"
    echo "  📁 Companion: http://localhost:3020"
    echo ""
    echo "Production URLs (after DNS setup):"
    echo "  🌐 Main Site: https://scientistcloud.com"
    echo "  📱 Data Portal: https://scientistcloud.com/portal"
    echo "  🔧 Health: https://scientistcloud.com/portal/health"
    echo ""
    echo "Useful Commands:"
    echo "  📊 View logs: docker-compose logs -f"
    echo "  🔄 Restart: docker-compose restart"
    echo "  🛑 Stop: docker-compose down"
    echo "  🧹 Clean: docker-compose down -v --rmi all"
    echo ""
}

# Main deployment function
deploy() {
    print_status "Starting unified deployment process..."
    
    check_docker
    check_existing_systems
    check_env
    check_sclib
    check_ssl
    build_containers
    start_services
    wait_for_services
    check_health
    integrate_nginx
    test_integration
    show_access_info
    
    print_success "Unified deployment completed successfully!"
}

# Handle command line arguments
case "${1:-start}" in
    "start")
        deploy
        ;;
    "deploy")
        deploy
        ;;
    "stop")
        print_status "Stopping services..."
        docker-compose down
        print_success "Services stopped"
        ;;
    "restart")
        print_status "Restarting services..."
        # First try to restart existing containers
        if docker-compose ps | grep -q "scientistcloud-portal"; then
            docker-compose restart
        else
            # If container doesn't exist or is stopped, start it
            print_status "Container not running, starting it..."
            docker-compose up -d
        fi
        print_success "Services restarted"
        ;;
    "logs")
        print_status "Showing logs..."
        docker-compose logs -f
        ;;
    "status")
        print_status "Portal service status:"
        docker-compose ps
        echo ""
        print_status "Existing systems status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(visstore|sclib)"
        ;;
    "test")
        print_status "Testing integration..."
        test_integration
        ;;
    "clean")
        print_status "Cleaning up..."
        docker-compose down -v --rmi all
        print_success "Cleanup completed"
        ;;
    "rebuild")
        print_status "Rebuilding containers..."
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        print_success "Containers rebuilt successfully"
        print_status "Installing dependencies..."
        sleep 5
        install_dependencies
        print_status "Testing SCLib API connection..."
        sleep 10
        if curl -f http://127.0.0.1:8080/test-sclib-api.php &> /dev/null; then
            print_success "SCLib API connection test passed"
        else
            print_warning "SCLib API connection test failed - check logs"
        fi
        ;;
    "install-deps")
        print_status "Installing PHP dependencies..."
        install_dependencies
        print_success "Dependency installation completed"
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start the portal with unified integration (default)"
        echo "  stop     - Stop portal services"
        echo "  restart  - Restart portal services"
        echo "  logs     - Show portal logs"
        echo "  status   - Show service status"
        echo "  test     - Test integration"
        echo "  clean    - Stop and remove portal containers/images"
        echo "  rebuild  - Rebuild containers"
        echo "  install-deps - Install/update PHP dependencies in container"
        echo "  help     - Show this help message"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
