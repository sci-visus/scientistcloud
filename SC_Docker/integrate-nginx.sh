#!/bin/bash

# ScientistCloud Data Portal - Nginx Integration Script
# This script integrates the portal with your existing VisusDataPortalPrivate nginx setup

set -e

echo "🔧 ScientistCloud Data Portal - Nginx Integration"
echo "================================================"

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

# Paths
VISUS_NGINX_PATH="/home/amy/VisStoreClone/visus-dataportal-private/Docker/nginx/conf.d"
PORTAL_NGINX_PATH="./nginx/portal.conf"

print_status "Integrating portal with existing nginx setup..."

# Check if VisusDataPortalPrivate nginx directory exists
if [ ! -d "$VISUS_NGINX_PATH" ]; then
    print_error "VisusDataPortalPrivate nginx directory not found: $VISUS_NGINX_PATH"
    print_error "Please make sure VisusDataPortalPrivate is in the expected location"
    exit 1
fi

# Check if portal nginx config exists
if [ ! -f "$PORTAL_NGINX_PATH" ]; then
    print_error "Portal nginx configuration not found: $PORTAL_NGINX_PATH"
    exit 1
fi

# Copy portal configuration to existing nginx setup
print_status "Copying portal configuration to existing nginx setup..."
cp "$PORTAL_NGINX_PATH" "$VISUS_NGINX_PATH/portal.conf"

if [ $? -eq 0 ]; then
    print_success "Portal configuration copied to $VISUS_NGINX_PATH/portal.conf"
else
    print_error "Failed to copy portal configuration"
    exit 1
fi

# Check if visstore_nginx is running
print_status "Checking if visstore_nginx is running..."
if docker ps --format "table {{.Names}}" | grep -q "visstore_nginx"; then
    print_success "visstore_nginx is running"
    
    # Reload nginx configuration
    print_status "Reloading nginx configuration..."
    docker exec visstore_nginx nginx -s reload
    
    if [ $? -eq 0 ]; then
        print_success "Nginx configuration reloaded successfully"
    else
        print_warning "Failed to reload nginx configuration"
        print_warning "You may need to restart visstore_nginx manually"
    fi
else
    print_warning "visstore_nginx is not running"
    print_warning "Please start your VisusDataPortalPrivate system first"
fi

print_success "Portal nginx integration completed!"
echo ""
echo "🌐 Portal will be accessible at:"
echo "  📱 https://scientistcloud.com/portal"
echo "  🔧 https://scientistcloud.com/portal/health"
echo ""
echo "📝 Next steps:"
echo "  1. Start your VisusDataPortalPrivate system:"
echo "     cd /home/amy/VisStoreClone/visus-dataportal-private/Docker"
echo "     docker-compose up -d"
echo ""
echo "  2. Deploy the portal:"
echo "     cd //home/amy/ScientistCloud2.0/SC_Dataportal/scientistcloud/SC_Docker"
echo "     ./deploy.sh deploy"
echo ""
echo "  3. Access the portal at https://scientistcloud.com/portal"
