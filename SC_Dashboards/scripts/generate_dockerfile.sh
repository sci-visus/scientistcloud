#!/bin/bash
# Generate Dockerfile from dashboard.json configuration
# Usage: ./generate_dockerfile.sh <dashboard_name>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="$(cd "$SCRIPT_DIR/../dashboards" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

# Try multiple possible paths for SCLib_Dashboards
SCLIB_DASHBOARDS_DIR=""
POSSIBLE_PATHS=(
    "$SCRIPT_DIR/../../scientistCloudLib/SCLib_Dashboards"
    "$SCRIPT_DIR/../../../scientistCloudLib/SCLib_Dashboards"
    "/Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards"
    "$(cd "$SCRIPT_DIR/../.." && pwd)/scientistCloudLib/SCLib_Dashboards"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        SCLIB_DASHBOARDS_DIR="$(cd "$path" && pwd)"
        break
    fi
done

if [ -z "$SCLIB_DASHBOARDS_DIR" ]; then
    echo "Warning: SCLib_Dashboards directory not found. Shared utilities will not be copied."
    echo "   Tried paths:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        echo "     - $path"
    done
    SCLIB_DASHBOARDS_DIR=""
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <dashboard_name>"
    exit 1
fi

DASHBOARD_NAME="$1"

# Flat structure: {name}.json in dashboards directory
CONFIG_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.json"
ENTRY_POINT_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.py"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Dashboard configuration not found: $CONFIG_FILE"
    exit 1
fi

# Load configuration using jq
BASE_IMAGE=$(jq -r '.base_image' "$CONFIG_FILE")
BASE_IMAGE_TAG=$(jq -r '.base_image_tag // "latest"' "$CONFIG_FILE")
ENTRY_POINT=$(jq -r '.entry_point' "$CONFIG_FILE")
ENTRY_POINT_TYPE=$(jq -r '.entry_point_type // "python"' "$CONFIG_FILE")
DASHBOARD_TYPE=$(jq -r '.type' "$CONFIG_FILE")
REQUIREMENTS_FILE=$(jq -r '.requirements_file // empty' "$CONFIG_FILE")
ADDITIONAL_REQUIREMENTS=$(jq -r '.additional_requirements | if length > 0 then join(" ") else "" end' "$CONFIG_FILE")
SHARED_UTILITIES=$(jq -r '.shared_utilities[]' "$CONFIG_FILE" 2>/dev/null | tr '\n' ' ' || echo "")
DASHBOARD_VERSION=$(jq -r '.version // "1.0.0"' "$CONFIG_FILE")
DASHBOARD_PORT=$(jq -r '.port' "$CONFIG_FILE")
HEALTH_CHECK_PATH=$(jq -r '.health_check_path // empty' "$CONFIG_FILE")
BUILD_ARGS=$(jq -r '.build_args // {} | keys[]' "$CONFIG_FILE" 2>/dev/null | tr '\n' ' ' || echo "")
ENVIRONMENT_VARS=$(jq -r '.environment_variables // {}' "$CONFIG_FILE")

# For flat structure, entry point should match dashboard name
# Default to {name}.py if entry_point is not specified or matches pattern
if [ -z "$ENTRY_POINT" ] || [ "$ENTRY_POINT" = "plotly_dashboard.py" ] || [ "$ENTRY_POINT" = "dashboard.py" ]; then
    # Check if .py or .ipynb exists
    if [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}.py" ]; then
        ENTRY_POINT="${DASHBOARD_NAME}.py"
    elif [ -f "$DASHBOARDS_DIR/${DASHBOARD_NAME}.ipynb" ]; then
        ENTRY_POINT="${DASHBOARD_NAME}.ipynb"
    fi
fi

# Default requirements file to {name}_requirements.txt if not specified
if [ -z "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE="${DASHBOARD_NAME}_requirements.txt"
fi

# Build shared utilities section - use relative paths from build context
# Build context is dashboards directory, so we need to copy from SCLib_Dashboards
# We'll need to copy SCLib_Dashboards files into the build context or use a different approach
# For now, assume SCLib_Dashboards will be in the build context
SHARED_UTILITIES_SECTION=""
if [ -n "$SHARED_UTILITIES" ]; then
    for util in $SHARED_UTILITIES; do
        # Use relative path from build context (dashboards directory)
        # SCLib_Dashboards should be copied to build context or mounted
        # For now, assume it's in a subdirectory or use absolute COPY from context
        SHARED_UTILITIES_SECTION="${SHARED_UTILITIES_SECTION}# Copy shared utility: $util\n"
        if [ -n "$SCLIB_DASHBOARDS_DIR" ] && [ -f "$SCLIB_DASHBOARDS_DIR/$util" ]; then
            # Note: In Docker build context, we need to copy these files
            # For now, assume they'll be in the build context at SCLib_Dashboards/$util
            SHARED_UTILITIES_SECTION="${SHARED_UTILITIES_SECTION}COPY SCLib_Dashboards/$util ./$util\n"
        fi
    done
fi

# Build environment variables section
ENVIRONMENT_VARIABLES_SECTION=""
if [ -n "$ENVIRONMENT_VARS" ] && [ "$ENVIRONMENT_VARS" != "{}" ]; then
    while IFS= read -r line; do
        if [[ "$line" =~ \"([^\"]+)\":\ *\"([^\"]+)\" ]]; then
            KEY="${BASH_REMATCH[1]}"
            VALUE="${BASH_REMATCH[2]}"
            ENVIRONMENT_VARIABLES_SECTION="${ENVIRONMENT_VARIABLES_SECTION}ENV ${KEY}=${VALUE}\n"
        fi
    done < <(echo "$ENVIRONMENT_VARS" | jq -r 'to_entries[] | "\(.key):\(.value)"' 2>/dev/null || echo "")
fi

# Build CMD section based on dashboard type
CMD_SECTION=""
if [ "$ENTRY_POINT_TYPE" = "notebook" ]; then
    CMD_SECTION="CMD [\"voila\", \"${ENTRY_POINT}\", \"--port=${DASHBOARD_PORT}\", \"--no-browser\", \"--autoreload\"]"
elif [ "$DASHBOARD_TYPE" = "dash" ]; then
    CMD_SECTION="CMD [\"python3\", \"${ENTRY_POINT}\"]"
elif [ "$DASHBOARD_TYPE" = "bokeh" ]; then
    # Bokeh needs special command with bokeh serve
    CMD_SECTION="CMD [\"sh\", \"-c\", \"python3 -m bokeh serve ./${ENTRY_POINT} --allow-websocket-origin=\${DOMAIN_NAME} --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=${DASHBOARD_PORT} --address=0.0.0.0 --use-xheaders --session-token-expiration=86400\"]"
elif [ "$DASHBOARD_TYPE" = "panel" ]; then
    # Panel needs panel serve command
    CMD_SECTION="CMD [\"sh\", \"-c\", \"python3 -m panel serve ./${ENTRY_POINT} --allow-websocket-origin=\${DOMAIN_NAME} --port=${DASHBOARD_PORT} --address=0.0.0.0 --use-xheaders\"]"
else
    CMD_SECTION="CMD [\"python3\", \"${ENTRY_POINT}\"]"
fi

# Generate Dockerfile from template
TEMPLATE_FILE="$TEMPLATES_DIR/Dockerfile.template"
OUTPUT_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.Dockerfile"

# Simple template replacement (using sed for portability)
sed -e "s|{{BASE_IMAGE}}|$BASE_IMAGE|g" \
    -e "s|{{BASE_IMAGE_TAG}}|$BASE_IMAGE_TAG|g" \
    -e "s|{{DASHBOARD_NAME}}|$DASHBOARD_NAME|g" \
    -e "s|{{DASHBOARD_VERSION}}|$DASHBOARD_VERSION|g" \
    -e "s|{{DASHBOARD_TYPE}}|$DASHBOARD_TYPE|g" \
    -e "s|{{ENTRY_POINT}}|$ENTRY_POINT|g" \
    -e "s|{{ENTRY_POINT_TYPE}}|$ENTRY_POINT_TYPE|g" \
    -e "s|{{DASHBOARD_PORT}}|$DASHBOARD_PORT|g" \
    -e "s|{{REQUIREMENTS_FILE}}|$REQUIREMENTS_FILE|g" \
    -e "s|{{ADDITIONAL_REQUIREMENTS}}|$ADDITIONAL_REQUIREMENTS|g" \
    -e "s|{{HEALTH_CHECK_PATH}}|$HEALTH_CHECK_PATH|g" \
    -e "s|{{SHARED_UTILITIES_SECTION}}|$SHARED_UTILITIES_SECTION|g" \
    -e "s|{{ENVIRONMENT_VARIABLES_SECTION}}|$ENVIRONMENT_VARIABLES_SECTION|g" \
    -e "s|{{CMD_SECTION}}|$CMD_SECTION|g" \
    "$TEMPLATE_FILE" > "$OUTPUT_FILE"

# Handle conditional sections
if [ -n "$REQUIREMENTS_FILE" ]; then
    sed -i.bak 's|{{#if REQUIREMENTS_FILE}}|#|g; s|{{/if}}||g' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
else
    sed -i.bak '/{{#if REQUIREMENTS_FILE}}/,/{{/if}}/d' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
fi

# Handle ADDITIONAL_REQUIREMENTS conditional
if [ -n "$ADDITIONAL_REQUIREMENTS" ]; then
    sed -i.bak 's|{{#if ADDITIONAL_REQUIREMENTS}}|#|g; s|{{/if}}||g' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
else
    sed -i.bak '/{{#if ADDITIONAL_REQUIREMENTS}}/,/{{/if}}/d' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
fi

# Handle HEALTH_CHECK_PATH conditional
if [ -n "$HEALTH_CHECK_PATH" ]; then
    sed -i.bak 's|{{#if HEALTH_CHECK_PATH}}|#|g; s|{{/if}}||g' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
else
    sed -i.bak '/{{#if HEALTH_CHECK_PATH}}/,/{{/if}}/d' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
fi

# Handle BUILD_ARGS (if any)
if [ -n "$BUILD_ARGS" ]; then
    BUILD_ARGS_SECTION=""
    for arg in $BUILD_ARGS; do
        BUILD_ARGS_SECTION="${BUILD_ARGS_SECTION}ARG ${arg}\n"
    done
    # Replace the BUILD_ARGS block with actual ARG lines
    sed -i.bak "s|{{#if BUILD_ARGS}}|#|g; s|{{#each BUILD_ARGS}}|#|g; s|{{/each}}||g; s|{{/if}}||g" "$OUTPUT_FILE"
    # Insert BUILD_ARGS after the comment
    sed -i.bak "/^# Build arguments$/a\\
${BUILD_ARGS_SECTION}" "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
else
    sed -i.bak '/{{#if BUILD_ARGS}}/,/{{/if}}/d' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"
fi

echo "✅ Generated Dockerfile: $OUTPUT_FILE"
