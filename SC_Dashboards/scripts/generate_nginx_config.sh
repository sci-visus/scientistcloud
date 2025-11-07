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
DASHBOARD_TYPE=$(jq -r '.type // "dash"' "$CONFIG_FILE")
HEALTH_CHECK_PATH=$(jq -r '.health_check_path // empty' "$CONFIG_FILE")
ENABLE_CORS=$(jq -r '.enable_cors // false' "$CONFIG_FILE")
# Get app_path (where the dashboard app is mounted, e.g., /plotly/ for Dash, /3DVTK/ for Bokeh)
APP_PATH=$(jq -r '.app_path // empty' "$CONFIG_FILE")
# If app_path is not specified, determine it based on dashboard type
if [ -z "$APP_PATH" ] || [ "$APP_PATH" == "null" ]; then
    if [[ "$DASHBOARD_TYPE" == "bokeh" ]]; then
        # For Bokeh apps, use the dashboard name as the app path
        # Prefer command line name (most accurate), fallback to config file name
        if [ -n "$DASHBOARD_NAME" ]; then
            APP_PATH="/${DASHBOARD_NAME}/"
        else
            # Fallback to dashboard name from config file
            DASHBOARD_NAME_FROM_CONFIG=$(jq -r '.name // empty' "$CONFIG_FILE")
            if [ -n "$DASHBOARD_NAME_FROM_CONFIG" ] && [ "$DASHBOARD_NAME_FROM_CONFIG" != "null" ]; then
                APP_PATH="/${DASHBOARD_NAME_FROM_CONFIG}/"
            else
                APP_PATH="/"
            fi
        fi
    else
        # For other types (Dash, Plotly), default to root
        APP_PATH="/"
    fi
fi
# Ensure app_path starts with / and ends with /
if [[ ! "$APP_PATH" =~ ^/ ]]; then
    APP_PATH="/$APP_PATH"
fi
if [[ ! "$APP_PATH" =~ /$ ]]; then
    APP_PATH="${APP_PATH}/"
fi
DASHBOARD_NAME_LOWER=$(echo "$DASHBOARD_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')

# Ensure NGINX_PATH has trailing slash (matches working pattern like /dataExplorer/)
if [[ ! "$NGINX_PATH" =~ /$ ]]; then
    NGINX_PATH="${NGINX_PATH}/"
fi
# Store path without trailing slash for backward compatibility (if needed elsewhere)
NGINX_PATH_WITHOUT_SLASH="${NGINX_PATH%/}"

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
    # Health check path should be at the app_path, not root
    HEALTH_CHECK_FULL_PATH="${APP_PATH}${HEALTH_CHECK_PATH#/}"  # Remove leading / from health_check_path if present
    # Remove trailing slash from NGINX_PATH to avoid double slashes
    NGINX_PATH_FOR_HEALTH="${NGINX_PATH%/}"
    # Remove leading slash from HEALTH_CHECK_PATH to avoid double slashes
    HEALTH_CHECK_PATH_CLEAN="${HEALTH_CHECK_PATH#/}"
    cat > "$HEALTH_TEMP" << HEALTHEOF
    location ${NGINX_PATH_FOR_HEALTH}/${HEALTH_CHECK_PATH_CLEAN} {
        # Use variable to defer hostname resolution (prevents startup errors if containers aren't up)
        set \$upstream_host "dashboard_${DASHBOARD_NAME_LOWER}";
        set \$upstream_port "${DASHBOARD_PORT}";
        proxy_pass http://\$upstream_host:\$upstream_port${HEALTH_CHECK_FULL_PATH};
        proxy_set_header Host \$host;
        access_log off;
    }
HEALTHEOF
else
    echo "    # Health check disabled" > "$HEALTH_TEMP"
fi

# Build static file section based on dashboard type
STATIC_TEMP=$(mktemp)
if [[ "$DASHBOARD_TYPE" == "plotly" ]]; then
    # Plotly/Dash uses /assets/ for static files (mounted at APP_PATH/assets/)
    cat > "$STATIC_TEMP" << STATICEOF
# Static files (assets)
location ${NGINX_PATH}assets/ {
    # Use variable to defer hostname resolution
    set \$upstream_host "dashboard_${DASHBOARD_NAME_LOWER}";
    set \$upstream_port "${DASHBOARD_PORT}";
    proxy_pass http://\$upstream_host:\$upstream_port${APP_PATH}assets/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For "\$proxy_add_x_forwarded_for";
    proxy_set_header X-Forwarded-Proto \$scheme;
}
STATICEOF
elif [[ "$DASHBOARD_TYPE" == "dash" ]]; then
    # Dash uses /assets/ for static files (mounted at APP_PATH/assets/)
    cat > "$STATIC_TEMP" << STATICEOF
# Static files (Dash - uses assets/)
location ${NGINX_PATH}assets/ {
    # Use variable to defer hostname resolution
    set \$upstream_host "dashboard_${DASHBOARD_NAME_LOWER}";
    set \$upstream_port "${DASHBOARD_PORT}";
    proxy_pass http://\$upstream_host:\$upstream_port${APP_PATH}assets/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For "\$proxy_add_x_forwarded_for";
    proxy_set_header X-Forwarded-Proto \$scheme;
}
STATICEOF
elif [[ "$DASHBOARD_TYPE" == "bokeh" ]]; then
    # Bokeh uses /static/ for static files (shared across all apps, served from root)
    cat > "$STATIC_TEMP" << STATICEOF
# Static files (Bokeh - uses static/ at root level, not app path)
location ${NGINX_PATH}static/ {
    # Use variable to defer hostname resolution
    set \$upstream_host "dashboard_${DASHBOARD_NAME_LOWER}";
    set \$upstream_port "${DASHBOARD_PORT}";
    # Bokeh serves static files from /static/ at root, not from app path
    proxy_pass http://\$upstream_host:\$upstream_port/static/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For "\$proxy_add_x_forwarded_for";
    proxy_set_header X-Forwarded-Proto \$scheme;
}
STATICEOF
else
    # Other types (vtk, etc.) - no static file section
    echo "# Static files not configured for type: $DASHBOARD_TYPE" > "$STATIC_TEMP"
fi

# Build Bokeh/Dash specific headers section
BOKEH_HEADERS_TEMP=$(mktemp)
if [[ "$DASHBOARD_TYPE" == "bokeh" || "$DASHBOARD_TYPE" == "dash" ]]; then
    cat > "$BOKEH_HEADERS_TEMP" << BOKEHEOF
    proxy_cookie_path / ${NGINX_PATH};
    
    # WebSocket support for Bokeh/Dash
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    # Connection header for WebSocket upgrade
    # Note: The main nginx config should have: map \$http_upgrade \$connection_upgrade { default upgrade; '' close; }
    # If that map exists, use: proxy_set_header Connection \$connection_upgrade;
    # Otherwise, for Bokeh apps that always use WebSockets, we can set to upgrade
    proxy_set_header Connection "upgrade";
    
    # Bokeh/Dash-specific headers
    proxy_set_header X-Forwarded-Prefix ${NGINX_PATH};
    proxy_redirect off;
BOKEHEOF
else
    cat > "$BOKEH_HEADERS_TEMP" << BOKEHEOF
    # WebSocket support (if needed)
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    set \$connection_upgrade "upgrade";
    if (\$http_upgrade = '') {
        set \$connection_upgrade "close";
    }
    proxy_set_header Connection \$connection_upgrade;
BOKEHEOF
fi

# Build the config file using a here-document approach
TEMP_CONFIG=$(mktemp)
sed -e "s|{{DASHBOARD_NAME}}|$DASHBOARD_NAME|g" \
    -e "s|{{DASHBOARD_NAME_LOWER}}|$DASHBOARD_NAME_LOWER|g" \
    -e "s|{{NGINX_PATH}}|$NGINX_PATH|g" \
    -e "s|{{NGINX_PATH_WITHOUT_SLASH}}|$NGINX_PATH_WITHOUT_SLASH|g" \
    -e "s|{{DASHBOARD_PORT}}|$DASHBOARD_PORT|g" \
    -e "s|{{DASHBOARD_TYPE}}|$DASHBOARD_TYPE|g" \
    -e "s|{{DOMAIN_NAME}}|$DOMAIN_NAME|g" \
    -e "s|{{APP_PATH}}|$APP_PATH|g" \
    "$TEMPLATE_FILE" > "$TEMP_CONFIG"

# Replace the section placeholders with actual content
# Use awk to handle multi-line replacements properly
awk -v cors_file="$CORS_TEMP" -v health_file="$HEALTH_TEMP" -v static_file="$STATIC_TEMP" -v bokeh_file="$BOKEH_HEADERS_TEMP" '
    /{{CORS_SECTION}}/ {
        while ((getline line < cors_file) > 0) {
            print line
        }
        close(cors_file)
        next
    }
    /{{BOKEH_DASH_HEADERS}}/ {
        while ((getline line < bokeh_file) > 0) {
            print line
        }
        close(bokeh_file)
        next
    }
    /{{STATIC_FILES_SECTION}}/ {
        while ((getline line < static_file) > 0) {
            print line
        }
        close(static_file)
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
rm -f "$CORS_TEMP" "$HEALTH_TEMP" "$STATIC_TEMP" "$BOKEH_HEADERS_TEMP" "$TEMP_CONFIG"

echo "✅ Generated nginx configuration: $OUTPUT_FILE"
echo "   Add this to your main nginx configuration or include it in conf.d/"

