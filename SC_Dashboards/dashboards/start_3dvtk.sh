#!/bin/bash
# Startup script for 3DVTK dashboard
# Runs health check server in background and Bokeh server in foreground

# Start health check server in background
python3 /app/health_check_server.py &
HEALTH_CHECK_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down..."
    kill $HEALTH_CHECK_PID 2>/dev/null
    exit
}

# Trap signals
trap cleanup SIGTERM SIGINT

# Start Bokeh server
python3 -m bokeh serve ./3DVTK.py \
    --allow-websocket-origin=$DOMAIN_NAME \
    --allow-websocket-origin=127.0.0.1 \
    --allow-websocket-origin=0.0.0.0 \
    --port=8051 \
    --address=0.0.0.0 \
    --use-xheaders \
    --session-token-expiration=86400

# Cleanup on exit
cleanup

