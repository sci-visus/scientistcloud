# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM visstore-4d-dashboard-base:latest

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


# Copy dashboard-specific files (flat structure)
COPY 4d_dashboardopt.py ./
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
EXPOSE 8057

# Health check (if specified)

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8057/health || exit 1


# Run dashboard entry point
CMD ["sh", "-c", "python3 -m bokeh serve ./4d_dashboardopt.py --allow-websocket-origin=$DOMAIN_NAME --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=8057 --address=0.0.0.0 --use-xheaders --session-token-expiration=86400"]

