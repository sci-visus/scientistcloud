#!/bin/bash
# Startup script for 3DVTK dashboard
# Runs health check server in background and Bokeh server in foreground

echo "🚀 Starting 3DVTK Dashboard..."
echo "📋 Starting health check server on port 8052..."

# Start health check server in background
python3 /app/health_check_server.py > /tmp/health_check.log 2>&1 &
HEALTH_CHECK_PID=$!

# Wait a moment to ensure health check server starts
sleep 1

# Check if health check server is running
if ps -p $HEALTH_CHECK_PID > /dev/null; then
    echo "✅ Health check server started (PID: $HEALTH_CHECK_PID)"
else
    echo "⚠️ Health check server failed to start"
    cat /tmp/health_check.log 2>/dev/null || true
fi

# Function to cleanup on exit
cleanup() {
    echo "🛑 Shutting down..."
    if ps -p $HEALTH_CHECK_PID > /dev/null; then
        kill $HEALTH_CHECK_PID 2>/dev/null
        echo "✅ Health check server stopped"
    fi
    exit
}

# Trap signals
trap cleanup SIGTERM SIGINT

echo "📊 Starting Bokeh server on port 8051..."

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

