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
# Get additional requirements and check if array has any items
ADDITIONAL_REQUIREMENTS_RAW=$(jq -r '.additional_requirements // []' "$CONFIG_FILE")
ADDITIONAL_REQUIREMENTS_COUNT=$(echo "$ADDITIONAL_REQUIREMENTS_RAW" | jq 'length')
if [ "$ADDITIONAL_REQUIREMENTS_COUNT" -gt 0 ]; then
    ADDITIONAL_REQUIREMENTS=$(echo "$ADDITIONAL_REQUIREMENTS_RAW" | jq -r 'join(" ")')
else
    ADDITIONAL_REQUIREMENTS=""
fi
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
# First, copy the entire SCLib_Dashboards package directory if it exists in build context
# This is needed for dashboards that import SCLib_Dashboards as a package (e.g., 4d_dashboardLite)
if [ -n "$SCLIB_DASHBOARDS_DIR" ] && [ -d "$SCLIB_DASHBOARDS_DIR" ]; then
    SHARED_UTILITIES_SECTION="${SHARED_UTILITIES_SECTION}# Copy entire SCLib_Dashboards package directory\n"
    SHARED_UTILITIES_SECTION="${SHARED_UTILITIES_SECTION}COPY SCLib_Dashboards ./SCLib_Dashboards\n"
fi
# Also copy individual utility files (for backward compatibility)
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

# Check if VTK/PyVista is needed (check additional_requirements for vtk or pyvista)
NEEDS_VTK_X11=false
if [ "$ADDITIONAL_REQUIREMENTS_COUNT" -gt 0 ]; then
    # Check if any requirement contains vtk or pyvista (case insensitive)
    if echo "$ADDITIONAL_REQUIREMENTS_RAW" | jq -r '.[]' | grep -qiE '(vtk|pyvista)'; then
        NEEDS_VTK_X11=true
    fi
fi

# Build VTK X11 libraries section if needed
VTK_X11_SECTION=""
if [ "$NEEDS_VTK_X11" = true ]; then
    VTK_X11_SECTION="# Environment variables for headless VTK/PyVista rendering\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}ENV DISPLAY=:99\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}ENV QT_QPA_PLATFORM=offscreen\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}ENV MESA_GL_VERSION_OVERRIDE=3.3\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}ENV MESA_GLSL_VERSION_OVERRIDE=330\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}# Install system dependencies for PyVista/VTK rendering\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}RUN apt-get update && apt-get install -y --no-install-recommends \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libx11-6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxext6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxrender1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxtst6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxi6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxrandr2 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxss1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxcb1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxcomposite1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxcursor1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxdamage1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxfixes3 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxinerama1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxmu6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxpm4 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxaw7 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libxft2 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libfontconfig1 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libfreetype6 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libgl1-mesa-dri \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libglu1-mesa \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libglib2.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libgthread-2.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libgtk-3-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libgdk-pixbuf-xlib-2.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libcairo-gobject2 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libpango-1.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libpangocairo-1.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libatk1.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libcairo2 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}        libpangoft2-1.0-0 \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}    && apt-get clean \\\\\n"
    VTK_X11_SECTION="${VTK_X11_SECTION}    && rm -rf /var/lib/apt/lists/*\n"
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
    # DOMAIN_NAME should be set via environment variables from docker-compose
    CMD_SECTION="CMD [\"sh\", \"-c\", \"python3 -m bokeh serve ./${ENTRY_POINT} --allow-websocket-origin=\\\$DOMAIN_NAME --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=${DASHBOARD_PORT} --address=0.0.0.0 --use-xheaders --session-token-expiration=86400\"]"
elif [ "$DASHBOARD_TYPE" = "panel" ]; then
    # Panel needs panel serve command
    # DOMAIN_NAME should be set via environment variables from docker-compose
    CMD_SECTION="CMD [\"sh\", \"-c\", \"python3 -m panel serve ./${ENTRY_POINT} --allow-websocket-origin=\\\$DOMAIN_NAME --port=${DASHBOARD_PORT} --address=0.0.0.0 --use-xheaders\"]"
else
    CMD_SECTION="CMD [\"python3\", \"${ENTRY_POINT}\"]"
fi

# Generate Dockerfile from template
TEMPLATE_FILE="$TEMPLATES_DIR/Dockerfile.template"
OUTPUT_FILE="$DASHBOARDS_DIR/${DASHBOARD_NAME}.Dockerfile"

# First, handle conditional sections BEFORE template replacement
# Create a temporary file to process conditionals
TEMP_FILE="${OUTPUT_FILE}.tmp"
cp "$TEMPLATE_FILE" "$TEMP_FILE"

# Handle ADDITIONAL_REQUIREMENTS conditional
# Check if there are any additional requirements (explicit count check)
if [ "$ADDITIONAL_REQUIREMENTS_COUNT" -gt 0 ] && [ -n "$ADDITIONAL_REQUIREMENTS" ]; then
    # Keep the section, just remove the conditional markers
    sed -i.bak 's|{{#if ADDITIONAL_REQUIREMENTS}}||g; s|{{/if}}||g' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
else
    # Remove the entire conditional section (match from opening to closing tag)
    # Use a pattern that matches {{/if}} with escaped forward slash
    sed -i.bak '/{{#if ADDITIONAL_REQUIREMENTS}}/,/{{\/if}}/d' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
fi

# Handle HEALTH_CHECK_PATH conditional
if [ -n "$HEALTH_CHECK_PATH" ]; then
    # Keep the section, just remove the conditional markers
    sed -i.bak 's|{{#if HEALTH_CHECK_PATH}}||g; s|{{/if}}||g' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
else
    # Remove the entire conditional section (match from opening to closing tag)
    # Use a pattern that matches {{/if}} with escaped forward slash
    sed -i.bak '/{{#if HEALTH_CHECK_PATH}}/,/{{\/if}}/d' "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
fi

# Requirements file is always present (build script ensures it), so always include it
sed -i.bak 's|{{#if REQUIREMENTS_FILE}}||g; s|{{/if}}||g' "$TEMP_FILE"
rm -f "$TEMP_FILE.bak"

# Now do template replacement
# Handle VTK_X11_SECTION separately since it contains newlines
if [ -n "$VTK_X11_SECTION" ]; then
    # Use a temporary file to handle the replacement with newlines
    echo -e "$VTK_X11_SECTION" > /tmp/vtk_x11_section.txt
    # Replace the placeholder with the content from file
    sed -i.bak "/{{VTK_X11_SECTION}}/r /tmp/vtk_x11_section.txt" "$TEMP_FILE"
    sed -i.bak "s|{{VTK_X11_SECTION}}||g" "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak" /tmp/vtk_x11_section.txt
else
    # Remove the placeholder if VTK X11 is not needed
    sed -i.bak "s|{{VTK_X11_SECTION}}||g" "$TEMP_FILE"
    rm -f "$TEMP_FILE.bak"
fi

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
    "$TEMP_FILE" > "$OUTPUT_FILE"

# Clean up temp file
rm -f "$TEMP_FILE"

# Handle BUILD_ARGS (if any)
if [ -n "$BUILD_ARGS" ]; then
    # Add BUILD_ARGS before DEPLOY_SERVER
    for arg in $BUILD_ARGS; do
        sed -i.bak "/^ARG DEPLOY_SERVER$/i\\
ARG ${arg}\\
" "$OUTPUT_FILE"
    done
    rm -f "$OUTPUT_FILE.bak"
fi

# Add user/group configuration for permissions (after requirements install, before CMD)
# This allows bokehuser to write to mounted volumes like /mnt/visus_datasets
# Check if base image uses bokehuser (4d-dashboard-base, bokeh-dashboard-base, magicscan-base)
if echo "$BASE_IMAGE" | grep -qiE "(4d-dashboard|bokeh-dashboard|magicscan)"; then
    # Insert user/group configuration after requirements install
    PERMISSIONS_SECTION="# Fix permissions: Create bokehuser if it doesn't exist and add to www-data group\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}# This allows the dashboard to create sessions directories in /mnt/visus_datasets/upload/<UUID>/sessions\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}# IMPORTANT: Host directories at /mnt/visus_datasets/upload/<UUID> must have:\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}#   - Group ownership: www-data (or be group-writable)\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}#   - Permissions: 775 or 2775 (setgid) to allow group writes\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}#   Run on host: sudo chgrp -R www-data /mnt/visus_datasets/upload && sudo chmod -R g+w /mnt/visus_datasets/upload\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}USER root\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}RUN groupadd -f www-data && \\\\\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}    (id -u bokehuser >/dev/null 2>&1 || useradd -m -s /bin/bash -u 10001 bokehuser) && \\\\\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}    usermod -a -G www-data bokehuser && \\\\\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}    chown -R bokehuser:bokehuser /app\n"
    PERMISSIONS_SECTION="${PERMISSIONS_SECTION}USER bokehuser\n"
    
    # Find the line with "# Set environment variables" or "# Expose dashboard port" and insert before it
    if grep -q "# Set environment variables from configuration" "$OUTPUT_FILE"; then
        sed -i.bak "/^# Set environment variables from configuration$/i\\
${PERMISSIONS_SECTION}\\
" "$OUTPUT_FILE"
    elif grep -q "# Expose dashboard port" "$OUTPUT_FILE"; then
        sed -i.bak "/^# Expose dashboard port$/i\\
${PERMISSIONS_SECTION}\\
" "$OUTPUT_FILE"
    else
        # Insert before CMD if no other marker found
        sed -i.bak "/^CMD /i\\
${PERMISSIONS_SECTION}\\
" "$OUTPUT_FILE"
    fi
    rm -f "$OUTPUT_FILE.bak"
fi

echo "✅ Generated Dockerfile: $OUTPUT_FILE"
