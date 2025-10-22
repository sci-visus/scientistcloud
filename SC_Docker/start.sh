#!/bin/bash

# ScientistCloud Data Portal - Startup Script

echo "Starting ScientistCloud Data Portal..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from template..."
    if [ -f env.template ]; then
        cp env.template .env
        echo "Please edit .env file with your configuration values"
    else
        echo "Error: env.template not found"
        exit 1
    fi
fi

# Create logs directory
mkdir -p logs

# Check if SCLib directory exists
if [ ! -d "../scientistCloudLib" ]; then
    echo "Warning: SCLib directory not found at ../scientistCloudLib"
    echo "Please ensure SCLib is available for mounting"
fi

# Check if SC_Web directory exists
if [ ! -d "../SC_Web" ]; then
    echo "Error: SC_Web directory not found at ../SC_Web"
    exit 1
fi

echo "Building and starting containers..."

# Build and start
docker-compose up --build -d

echo "Waiting for services to start..."
sleep 10

# Check container status
echo "Container status:"
docker-compose ps

# Check logs
echo "Recent logs:"
docker-compose logs --tail=20 scientistcloud-portal

echo ""
echo "Portal should be available at:"
echo "  - http://localhost:8080"
echo "  - Test config: http://localhost:8080/test-config.php"
echo "  - Simple test: http://localhost:8080/test-simple.php"
echo ""
echo "To view logs: docker-compose logs -f scientistcloud-portal"
echo "To stop: docker-compose down"
