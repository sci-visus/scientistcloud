#!/bin/bash
# Register a dashboard in the dashboard registry
# Usage: ./register_dashboard.sh <dashboard_name> [config_file] [port] [nginx_path]
# If config_file not provided, will look for {name}.json in dashboards directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"

if [ -z "$1" ]; then
    echo "Usage: $0 <dashboard_name> [config_file] [port] [nginx_path]"
    exit 1
fi

DASHBOARD_NAME="$1"

# Find config file if not provided - flat structure only
if [ -z "$2" ]; then
    CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Error: Dashboard configuration not found: $CONFIG_FILE"
        exit 1
    fi
else
    CONFIG_FILE="$2"
fi

# Load config to get port and nginx_path if not provided
if [ -f "$CONFIG_FILE" ]; then
    DISPLAY_NAME=$(jq -r '.display_name // "'"$DASHBOARD_NAME"'"' "$CONFIG_FILE")
    PORT=${3:-$(jq -r '.port // 8050' "$CONFIG_FILE")}
    NGINX_PATH=${4:-$(jq -r '.nginx_path // "/dashboard/'$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]')'"' "$CONFIG_FILE")}
    # Use relative path for registry
    CONFIG_FILE_PATH="../dashboards/${DASHBOARD_NAME}.json"
else
    DISPLAY_NAME="$DASHBOARD_NAME"
    PORT=${3:-8050}
    NGINX_PATH=${4:-/dashboard/$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]')}
    CONFIG_FILE_PATH="../dashboards/${DASHBOARD_NAME}.json"
fi

# Update registry using jq
if [ ! -f "$REGISTRY_FILE" ]; then
    # Create initial registry
    cat > "$REGISTRY_FILE" <<EOF
{
  "version": "1.0.0",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "port_range": {
    "start": 8050,
    "end": 8999,
    "next_available": $((PORT + 1))
  },
  "dashboards": {}
}
EOF
fi

# Add or update dashboard entry
jq --arg name "$DASHBOARD_NAME" \
   --arg display "$DISPLAY_NAME" \
   --arg port "$PORT" \
   --arg path "$NGINX_PATH" \
   --arg config "$CONFIG_FILE_PATH" \
   '.dashboards[$name] = {
     "name": $name,
     "display_name": $display,
     "enabled": true,
     "port": ($port | tonumber),
     "nginx_path": $path,
     "config_file": $config
   } | .last_updated = "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"' \
   "$REGISTRY_FILE" > "$REGISTRY_FILE.tmp" && mv "$REGISTRY_FILE.tmp" "$REGISTRY_FILE"

echo "✅ Registered dashboard '$DASHBOARD_NAME' in registry"

