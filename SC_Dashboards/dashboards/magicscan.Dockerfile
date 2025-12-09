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
# Copy shared utility: msc_py.cpython-310-x86_64-linux-gnu.so
COPY SCLib_Dashboards/msc_py.cpython-310-x86_64-linux-gnu.so ./msc_py.cpython-310-x86_64-linux-gnu.so


# Copy dashboard-specific files (flat structure)
COPY magicscan.py ./
# Requirements file is always copied as requirements.txt in build context
# (build script ensures it exists, even if empty)
COPY requirements.txt ./requirements.txt

# Install dashboard-specific requirements (skip if file is empty)
RUN if [ -s requirements.txt ]; then \
        python3 -m pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "No requirements to install (requirements.txt is empty)"; \
    fi


# Fix permissions: Create bokehuser if it doesn't exist and add to www-data group
# This allows the dashboard to create sessions directories in /mnt/visus_datasets/upload/<UUID>/sessions
# IMPORTANT: Host directories at /mnt/visus_datasets/upload/<UUID> must have:
#   - Group ownership: www-data (or be group-writable)
#   - Permissions: 775 or 2775 (setgid) to allow group writes
#   Run on host: sudo chgrp -R www-data /mnt/visus_datasets/upload && sudo chmod -R g+w /mnt/visus_datasets/upload
USER root
RUN groupadd -f www-data && \
    (id -u bokehuser >/dev/null 2>&1 || useradd -m -s /bin/bash -u 10001 bokehuser) && \
    usermod -a -G www-data bokehuser && \
    chown -R bokehuser:bokehuser /app
USER bokehuser

# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8053

# Health check (if specified)

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8053/health || exit 1


# Run dashboard entry point
CMD ["sh", "-c", "python3 -m panel serve ./magicscan.py --allow-websocket-origin=$DOMAIN_NAME --port=8053 --address=0.0.0.0 --use-xheaders"]

