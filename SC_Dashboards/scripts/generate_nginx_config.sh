#!/bin/bash
# Generate nginx configuration from dashboard.json
# Usage: ./generate_nginx_config.sh <dashboard_name> [output_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

# Try multiple possible paths for nginx output directory
NGINX_OUTPUT_DIR=""
POSSIBLE_PATHS=(
    "$SCRIPT_DIR/../SC_Docker/nginx"
    "$SCRIPT_DIR/../../SC_Docker/nginx"
    "$SCRIPT_DIR/../../../scientistcloud/SC_Docker/nginx"
    "/Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker/nginx"
    "$(cd "$SCRIPT_DIR/../.." && pwd)/SC_Docker/nginx"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        NGINX_OUTPUT_DIR="$(cd "$path" && pwd)"
        break
    fi
done

# If no nginx directory found, use a local one
if [ -z "$NGINX_OUTPUT_DIR" ]; then
    NGINX_OUTPUT_DIR="$SCRIPT_DIR/../nginx"
    mkdir -p "$NGINX_OUTPUT_DIR/conf.d" 2>/dev/null || true
    echo "Warning: Using local nginx directory: $NGINX_OUTPUT_DIR"
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <dashboard_name> [output_file]"
    exit 1
fi

DASHBOARD_NAME="$1"

# Flat structure: {name}.json in dashboards directory
CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Dashboard configuration not found: $CONFIG_FILE"
    exit 1
fi

# Load configuration
NGINX_PATH=$(jq -r '.nginx_path' "$CONFIG_FILE")
DASHBOARD_PORT=$(jq -r '.port' "$CONFIG_FILE")
HEALTH_CHECK_PATH=$(jq -r '.health_check_path // empty' "$CONFIG_FILE")
ENABLE_CORS=$(jq -r '.enable_cors // false' "$CONFIG_FILE")
DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')

# Remove trailing "_dashboard" if present to avoid double "dashboard" in filename
# (e.g., "4D_Dashboard" -> "4d_dashboard" -> remove "_dashboard" -> "4d" -> "4d_dashboard.conf")
DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME_LOWER" | sed 's/_dashboard$//')

# Get domain name from environment or use default
DOMAIN_NAME="${DOMAIN_NAME:-${DEPLOY_SERVER#https://}}"
DOMAIN_NAME="${DOMAIN_NAME#http://}"
DOMAIN_NAME="${DOMAIN_NAME%/}"
if [ -z "$DOMAIN_NAME" ] || [ "$DOMAIN_NAME" = "${DOMAIN_NAME#*.}" ]; then
    # Fallback to default if not set or invalid
    DOMAIN_NAME="scientistcloud.com"
fi

# Determine output file
OUTPUT_NAME="${DASHBOARD_NAME_LOWER}_dashboard.conf"
if [ -n "$2" ]; then
    OUTPUT_FILE="$2"
else
    mkdir -p "$NGINX_OUTPUT_DIR/conf.d"
    OUTPUT_FILE="$NGINX_OUTPUT_DIR/conf.d/${OUTPUT_NAME}"
fi

# Generate nginx config from template
TEMPLATE_FILE="$TEMPLATES_DIR/nginx-config.template"

# Build CORS section (if enabled) - write to temp file for multi-line handling
CORS_TEMP=$(mktemp)
if [ "$ENABLE_CORS" = "true" ]; then
    cat > "$CORS_TEMP" << 'CORSEOF'
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
CORSEOF
else
    echo "        # CORS disabled" > "$CORS_TEMP"
fi

# Build health check section (if specified) - write to temp file for multi-line handling
HEALTH_TEMP=$(mktemp)
if [ -n "$HEALTH_CHECK_PATH" ]; then
    cat > "$HEALTH_TEMP" << HEALTHEOF
    location ${NGINX_PATH}${HEALTH_CHECK_PATH} {
        proxy_pass http://dashboard_${DASHBOARD_NAME_LOWER}:${DASHBOARD_PORT}${HEALTH_CHECK_PATH};
        proxy_set_header Host \$host;
        access_log off;
    }
HEALTHEOF
else
    echo "    # Health check disabled" > "$HEALTH_TEMP"
fi

# Build the config file using a here-document approach
TEMP_CONFIG=$(mktemp)
sed -e "s|{{DASHBOARD_NAME}}|$DASHBOARD_NAME|g" \
    -e "s|{{DASHBOARD_NAME_LOWER}}|$DASHBOARD_NAME_LOWER|g" \
    -e "s|{{NGINX_PATH}}|$NGINX_PATH|g" \
    -e "s|{{DASHBOARD_PORT}}|$DASHBOARD_PORT|g" \
    -e "s|{{DOMAIN_NAME}}|$DOMAIN_NAME|g" \
    "$TEMPLATE_FILE" > "$TEMP_CONFIG"

# Replace the section placeholders with actual content
# Use awk to handle multi-line replacements properly
awk -v cors_file="$CORS_TEMP" -v health_file="$HEALTH_TEMP" '
    /{{CORS_SECTION}}/ {
        while ((getline line < cors_file) > 0) {
            print line
        }
        close(cors_file)
        next
    }
    /{{HEALTH_CHECK_SECTION}}/ {
        while ((getline line < health_file) > 0) {
            print line
        }
        close(health_file)
        next
    }
    { print }
' "$TEMP_CONFIG" > "$OUTPUT_FILE"

# Cleanup temp files
rm -f "$CORS_TEMP" "$HEALTH_TEMP" "$TEMP_CONFIG"

echo "✅ Generated nginx configuration: $OUTPUT_FILE"
echo "   Add this to your main nginx configuration or include it in conf.d/"

