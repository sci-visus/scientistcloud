# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM visstore-bokeh-dashboard-base:latest

# Build arguments
ARG D_GIT_TOKEN

ARG DEPLOY_SERVER
ARG DOMAIN_NAME

# Environment Variables (inherited from base image)
ENV DEPLOY_SERVER=${DEPLOY_SERVER}
ENV DOMAIN_NAME=${DOMAIN_NAME}

# Echo build information
RUN echo "DEPLOY SERVER: ${DEPLOY_SERVER}"


# Copy application code
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Copy shared dashboard utilities from SCLib_Dashboards
# Copy entire SCLib_Dashboards package directory
COPY SCLib_Dashboards ./SCLib_Dashboards
# Copy shared utility: mongo_connection.py
COPY SCLib_Dashboards/mongo_connection.py ./mongo_connection.py
# Copy shared utility: utils_bokeh_mongodb.py
COPY SCLib_Dashboards/utils_bokeh_mongodb.py ./utils_bokeh_mongodb.py
# Copy shared utility: utils_bokeh_dashboard.py
COPY SCLib_Dashboards/utils_bokeh_dashboard.py ./utils_bokeh_dashboard.py
# Copy shared utility: utils_bokeh_auth.py
COPY SCLib_Dashboards/utils_bokeh_auth.py ./utils_bokeh_auth.py
# Copy shared utility: utils_bokeh_param.py
COPY SCLib_Dashboards/utils_bokeh_param.py ./utils_bokeh_param.py
# Copy shared utility: SCDash_dataset_resolver.py
COPY SCLib_Dashboards/SCDash_dataset_resolver.py ./SCDash_dataset_resolver.py
# Copy shared utility: ornl_chess_strain_lib.py
COPY SCLib_Dashboards/ornl_chess_strain_lib.py ./ornl_chess_strain_lib.py


# Copy dashboard-specific files (flat structure)
COPY ORNL_CHESS_strain.py ./
# Requirements file is always copied as requirements.txt in build context
# (build script ensures it exists, even if empty)
COPY requirements.txt ./requirements.txt

# Install dashboard-specific requirements (skip if file is empty)
RUN if [ -s requirements.txt ]; then \
        python3 -m pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "No requirements to install (requirements.txt is empty)"; \
    fi


# Fix permissions: Create bokehuser if it doesn't exist and add to www-data groupn# This allows the dashboard to create sessions directories in /mnt/visus_datasets/upload/<UUID>/sessionsn# IMPORTANT: Host directories at /mnt/visus_datasets/upload/<UUID> must have:n#   - Group ownership: www-data (or be group-writable)n#   - Permissions: 775 or 2775 (setgid) to allow group writesn#   Run on host: sudo chgrp -R www-data /mnt/visus_datasets/upload && sudo chmod -R g+w /mnt/visus_datasets/uploadnUSER rootnRUN groupadd -f www-data && \n    (id -u bokehuser >/dev/null 2>&1 || useradd -m -s /bin/bash -u 10001 bokehuser) && \n    usermod -a -G www-data bokehuser && \n    chown -R bokehuser:bokehuser /appnUSER bokehusern

# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8059

# Health check (if specified)

# Run dashboard entry point
CMD ["sh", "-c", "WS_ORIGIN=${DOMAIN_NAME:-scientistcloud.com}; python3 -m bokeh serve ./ORNL_CHESS_strain.py --allow-websocket-origin=$WS_ORIGIN --allow-websocket-origin=scientistcloud.com --allow-websocket-origin=www.scientistcloud.com --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=8059 --address=0.0.0.0 --use-xheaders --session-token-expiration=86400"]

