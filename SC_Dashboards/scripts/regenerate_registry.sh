#!/bin/bash
# Regenerate dashboard registry from actual files in dashboards directory
# This ensures registry keys match the actual filenames
# Usage: ./regenerate_registry.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
REGISTRY_FILE="$CONFIG_DIR/dashboard-registry.json"

echo "Regenerating dashboard registry from files in: $DASHBOARDS_DIR"
echo ""

# Initialize registry (start with empty dashboards to remove deleted ones)
cat > "$REGISTRY_FILE" <<EOF
{
  "version": "1.0.0",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "port_range": {
    "start": 8050,
    "end": 8999,
    "next_available": 8065
  },
  "dashboards": {}
}
EOF

# Find all .json files in dashboards directory
DASHBOARD_COUNT=0
for CONFIG_FILE in "$DASHBOARDS_DIR"/*.json; do
    # Skip if no files found (glob doesn't match)
    [ -f "$CONFIG_FILE" ] || continue
    
    # Skip demo or test files
    BASENAME=$(basename "$CONFIG_FILE" .json)
    if [[ "$BASENAME" == demo_* ]] || [[ "$BASENAME" == test_* ]]; then
        continue
    fi
    
    echo "Registering: $BASENAME"
    
    # Get config file basename (this becomes the registry key)
    CONFIG_BASENAME=$(basename "$CONFIG_FILE" .json)
    
    # Load values from config file
    DISPLAY_NAME=$(jq -r '.display_name // "'"$CONFIG_BASENAME"'"' "$CONFIG_FILE")
    PORT=$(jq -r '.port // 8050' "$CONFIG_FILE")
    NGINX_PATH=$(jq -r '.nginx_path // "/dashboard/'$(echo "$CONFIG_BASENAME" | tr '[:upper:]' '[:lower:]')'"' "$CONFIG_FILE")
    CONFIG_FILE_PATH="../dashboards/${CONFIG_BASENAME}.json"
    
    # Register in registry using the filename as the key
    jq --arg key "$CONFIG_BASENAME" \
       --arg name "$CONFIG_BASENAME" \
       --arg display "$DISPLAY_NAME" \
       --arg port "$PORT" \
       --arg path "$NGINX_PATH" \
       --arg config "$CONFIG_FILE_PATH" \
       '.dashboards[$key] = {
         "name": $name,
         "display_name": $display,
         "enabled": true,
         "port": ($port | tonumber),
         "nginx_path": $path,
         "config_file": $config
       } | .last_updated = "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"' \
       "$REGISTRY_FILE" > "$REGISTRY_FILE.tmp" && mv "$REGISTRY_FILE.tmp" "$REGISTRY_FILE"
    
    DASHBOARD_COUNT=$((DASHBOARD_COUNT + 1))
done

# Update port-registry.json with ports from regenerated registry
PORT_REGISTRY="$CONFIG_DIR/port-registry.json"
if [ ! -f "$PORT_REGISTRY" ]; then
    # Create initial port registry
    cat > "$PORT_REGISTRY" <<EOF
{
  "version": "1.0.0",
  "reserved_ports": {},
  "port_range": {
    "start": 8050,
    "end": 8999
  },
  "next_available": 8050
}
EOF
fi

# Update reserved_ports from registry
# IMPORTANT: Start with empty reserved_ports to remove entries for deleted dashboards
PORT_REGISTRY_TEMP=$(mktemp)
jq '.reserved_ports = {}' "$PORT_REGISTRY" > "$PORT_REGISTRY_TEMP"

# Track which ports we've seen to detect duplicates
declare -A SEEN_PORTS

for CONFIG_FILE in "$DASHBOARDS_DIR"/*.json; do
    [ -f "$CONFIG_FILE" ] || continue
    BASENAME=$(basename "$CONFIG_FILE" .json)
    
    # Skip demo or test files
    if [[ "$BASENAME" == demo_* ]] || [[ "$BASENAME" == test_* ]]; then
        continue
    fi
    
    PORT=$(jq -r '.port // 8050' "$CONFIG_FILE")
    
    # Check for port conflicts
    if [[ -n "${SEEN_PORTS[$PORT]}" ]]; then
        echo "⚠️  Port conflict: $PORT is used by both ${SEEN_PORTS[$PORT]} and $BASENAME"
    else
        SEEN_PORTS[$PORT]=$BASENAME
    fi
    
    # Add to port registry
    PORT_REGISTRY_TEMP=$(echo "$PORT_REGISTRY_TEMP" | jq --arg port "$PORT" --arg name "$BASENAME" '.reserved_ports[$port] = $name')
done

# Calculate next available port (find the highest port + 1, or start from 8050)
NEXT_AVAILABLE=$(echo "$PORT_REGISTRY_TEMP" | jq '[.reserved_ports | to_entries[] | (.key | tonumber)] | if length > 0 then max + 1 else 8050 end')
PORT_REGISTRY_TEMP=$(echo "$PORT_REGISTRY_TEMP" | jq --arg next "$NEXT_AVAILABLE" '.next_available = ($next | tonumber)')

# Write updated port registry
mv "$PORT_REGISTRY_TEMP" "$PORT_REGISTRY"
echo "✅ Port registry updated (removed entries for deleted dashboards)"

echo ""
echo "✅ Registry regenerated with $DASHBOARD_COUNT dashboard(s)"
echo "   Registry file: $REGISTRY_FILE"

