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

# Simple template replacement
sed -e "s|{{DASHBOARD_NAME}}|$DASHBOARD_NAME|g" \
    -e "s|{{DASHBOARD_NAME_LOWER}}|$DASHBOARD_NAME_LOWER|g" \
    -e "s|{{NGINX_PATH}}|$NGINX_PATH|g" \
    -e "s|{{DASHBOARD_PORT}}|$DASHBOARD_PORT|g" \
    -e "s|{{HEALTH_CHECK_PATH}}|$HEALTH_CHECK_PATH|g" \
    -e "s|{{ENABLE_CORS}}|$ENABLE_CORS|g" \
    -e "s|\${DOMAIN_NAME}|$DOMAIN_NAME|g" \
    "$TEMPLATE_FILE" > "$OUTPUT_FILE"

# Handle conditional sections
# Note: macOS sed requires -i with extension, Linux doesn't - use .bak for compatibility
# We need to be careful not to delete the closing server block brace

# Use a temporary file approach to avoid sed range pattern issues
TEMP_FILE=$(mktemp)
cp "$OUTPUT_FILE" "$TEMP_FILE"

# Handle HEALTH_CHECK_PATH conditional
if [ -n "$HEALTH_CHECK_PATH" ]; then
    # Keep the health check section - just remove the conditional markers
    sed -i.bak 's|{{#if HEALTH_CHECK_PATH}}||g; s|{{/if}}||g' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
else
    # Delete the health check section (lines with the conditional markers)
    # Use awk to delete lines between {{#if HEALTH_CHECK_PATH}} and {{/if}}
    # Match the closing tag explicitly
    awk '/{{#if HEALTH_CHECK_PATH}}/{flag=1; next} /{{\/if}}/ && flag {flag=0; next} !flag' "$TEMP_FILE" > "$TEMP_FILE.tmp" && mv "$TEMP_FILE.tmp" "$TEMP_FILE"
fi

# Handle ENABLE_CORS conditional
if [ "$ENABLE_CORS" = "true" ]; then
    # Keep the CORS section - just remove the conditional markers
    sed -i.bak 's|{{#if ENABLE_CORS}}||g; s|{{/if}}||g' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
else
    # Delete the CORS section (lines with the conditional markers)
    # Use awk to delete lines between {{#if ENABLE_CORS}} and {{/if}}
    # Match the closing tag explicitly
    awk '/{{#if ENABLE_CORS}}/{flag=1; next} /{{\/if}}/ && flag {flag=0; next} !flag' "$TEMP_FILE" > "$TEMP_FILE.tmp" && mv "$TEMP_FILE.tmp" "$TEMP_FILE"
fi

# Replace original file with cleaned version
mv "$TEMP_FILE" "$OUTPUT_FILE"

# Verify the file ends with a closing brace for the server block
# If it doesn't, add it (safety check)
# Check the last non-empty line
LAST_NON_EMPTY=$(grep -v '^[[:space:]]*$' "$OUTPUT_FILE" | tail -1)
if [ -z "$LAST_NON_EMPTY" ] || ! echo "$LAST_NON_EMPTY" | grep -qE '^[[:space:]]*}[[:space:]]*$'; then
    # Ensure we have a newline, then add the closing brace
    if [ -s "$OUTPUT_FILE" ] && ! tail -c 1 "$OUTPUT_FILE" | grep -q .; then
        # File ends with newline, just add the brace
        echo "}" >> "$OUTPUT_FILE"
    else
        # File doesn't end with newline, add newline and brace
        echo "" >> "$OUTPUT_FILE"
        echo "}" >> "$OUTPUT_FILE"
    fi
    echo "   ⚠️  Added missing closing brace for server block"
fi

# Also verify the file starts with server block
if ! head -10 "$OUTPUT_FILE" | grep -q "^server {"; then
    echo "   ⚠️  Warning: Generated config may be missing server block"
fi

echo "✅ Generated nginx configuration: $OUTPUT_FILE"
echo "   Add this to your main nginx configuration or include it in conf.d/"

