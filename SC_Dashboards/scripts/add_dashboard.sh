#!/bin/bash
# Interactive script to add a new dashboard to ScientistCloud
# Usage: ./add_dashboard.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Add New Dashboard ===${NC}"
echo ""

# Prompt for dashboard information
read -p "Dashboard name (e.g., MyNewDashboard): " DASHBOARD_NAME
DASHBOARD_NAME=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# Check if dashboard already exists (flat structure: {name}.json)
if [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}.json" ]; then
    echo -e "${RED}Error: Dashboard '$DASHBOARD_NAME' already exists!${NC}"
    echo -e "${RED}   Found: $DASHBOARDS_DIR/${DASHBOARD_NAME}.json${NC}"
    exit 1
fi

read -p "Display name (e.g., My New Dashboard): " DISPLAY_NAME
read -p "Description: " DESCRIPTION
read -p "Dashboard type (dash/bokeh/jupyter/standalone) [dash]: " DASHBOARD_TYPE
DASHBOARD_TYPE=${DASHBOARD_TYPE:-dash}

read -p "Entry point file (e.g., my_dashboard.py): " ENTRY_POINT
read -p "Entry point type (python/notebook) [python]: " ENTRY_POINT_TYPE
ENTRY_POINT_TYPE=${ENTRY_POINT_TYPE:-python}

read -p "Requirements file (e.g., requirements.txt) [requirements.txt]: " REQUIREMENTS_FILE
REQUIREMENTS_FILE=${REQUIREMENTS_FILE:-requirements.txt}

read -p "Base image (e.g., plotly-dashboard-base) [plotly-dashboard-base]: " BASE_IMAGE
BASE_IMAGE=${BASE_IMAGE:-plotly-dashboard-base}

read -p "Base image tag [latest]: " BASE_IMAGE_TAG
BASE_IMAGE_TAG=${BASE_IMAGE_TAG:-latest}

read -p "Nginx path (e.g., /dashboard/mynew) [/dashboard/${DASHBOARD_NAME}]: " NGINX_PATH
NGINX_PATH=${NGINX_PATH:-/dashboard/${DASHBOARD_NAME}}

# Get next available port
PORT_REGISTRY="$CONFIG_DIR/port-registry.json"
NEXT_PORT=$(jq -r '.next_available' "$PORT_REGISTRY" 2>/dev/null || echo "8050")

read -p "Port [$NEXT_PORT]: " PORT
PORT=${PORT:-$NEXT_PORT}

echo ""
echo -e "${YELLOW}Creating dashboard configuration...${NC}"

# Flat structure: {name}.json in dashboards directory
DASHBOARD_DIR="$DASHBOARDS_DIR"
CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
ENTRY_POINT_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.py"
REQUIREMENTS_FILE_PATH="$DASHBOARDS_DIR/${DASHBOARD_NAME}_requirements.txt"

# Create dashboard.json
cat > "$CONFIG_FILE" <<EOF
{
  "name": "$DASHBOARD_NAME",
  "display_name": "$DISPLAY_NAME",
  "description": "$DESCRIPTION",
  "version": "1.0.0",
  "type": "$DASHBOARD_TYPE",
  "entry_point": "$ENTRY_POINT",
  "entry_point_type": "$ENTRY_POINT_TYPE",
  "port": $PORT,
  "base_image": "$BASE_IMAGE",
  "base_image_tag": "$BASE_IMAGE_TAG",
  "requirements_file": "$REQUIREMENTS_FILE",
  "additional_requirements": [],
  "shared_utilities": [
    "mongo_connection.py"
  ],
  "environment_variables": {
    "SECRET_KEY": "\${SECRET_KEY}",
    "DEPLOY_SERVER": "\${DEPLOY_SERVER}",
    "DB_NAME": "\${DB_NAME}",
    "MONGO_URL": "\${MONGO_URL}"
  },
  "nginx_path": "$NGINX_PATH",
  "health_check_path": "/health",
  "build_args": {
    "D_GIT_TOKEN": "\${D_GIT_TOKEN}"
  },
  "volume_mounts": [],
  "exposed_ports": [$PORT],
  "depends_on": [],
  "enabled": true
}
EOF

# Create placeholder files (flat structure)
if [ ! -f "$ENTRY_POINT_FILE" ]; then
    echo "# Dashboard entry point for $DISPLAY_NAME" > "$ENTRY_POINT_FILE"
fi
if [ ! -f "$REQUIREMENTS_FILE_PATH" ]; then
    echo "# Requirements for $DISPLAY_NAME" > "$REQUIREMENTS_FILE_PATH"
fi

# Update config to use flat structure naming
jq --arg entry "${DASHBOARD_NAME}.py" --arg req "${DASHBOARD_NAME}_requirements.txt" \
   '.entry_point = $entry | .requirements_file = $req' \
   "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

# Register dashboard in registry
echo -e "${YELLOW}Registering dashboard...${NC}"
"$SCRIPT_DIR/register_dashboard.sh" "$DASHBOARD_NAME" "$CONFIG_FILE" "$PORT" "$NGINX_PATH"

# Generate Dockerfile
echo -e "${YELLOW}Generating Dockerfile...${NC}"
"$SCRIPT_DIR/generate_dockerfile.sh" "$DASHBOARD_NAME"

# Generate nginx config
echo -e "${YELLOW}Generating nginx configuration...${NC}"
"$SCRIPT_DIR/generate_nginx_config.sh" "$DASHBOARD_NAME"

# Update next available port
NEXT_PORT=$((PORT + 1))
jq --arg next "$NEXT_PORT" '.next_available = ($next | tonumber) | .reserved_ports["'$PORT'"] = "'$DASHBOARD_NAME'"' "$PORT_REGISTRY" > "$PORT_REGISTRY.tmp" && mv "$PORT_REGISTRY.tmp" "$PORT_REGISTRY"

echo ""
echo -e "${GREEN}✅ Dashboard '$DASHBOARD_NAME' created successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit $ENTRY_POINT_FILE - Add your dashboard code"
echo "2. Edit $REQUIREMENTS_FILE_PATH - Add Python dependencies"
echo "3. Edit $CONFIG_FILE - Adjust configuration as needed"
echo "4. Run: ./scripts/build_dashboard.sh $DASHBOARD_NAME"
echo "5. Update docker-compose.yml to include the new service"
echo "6. Update nginx configuration to include the generated config"

