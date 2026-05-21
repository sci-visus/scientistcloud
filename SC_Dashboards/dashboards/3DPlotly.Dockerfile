# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM sc-plotly-dashboard-base:latest

# Build arguments
ARG D_GIT_TOKEN

ARG DEPLOY_SERVER
ARG DOMAIN_NAME

# Environment Variables (inherited from base image)
ENV DEPLOY_SERVER=${DEPLOY_SERVER}
ENV DOMAIN_NAME=${DOMAIN_NAME}

# Echo build information
RUN echo "DEPLOY SERVER: ${DEPLOY_SERVER}"

# Base images end as non-root; apt-get and permission fixes need root during build
USER root


# Environment variables for headless VTK/PyVista rendering
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=offscreen
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330

# Install system dependencies for PyVista/VTK rendering (Debian bookworm / python:3.10-slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxcb1 \
    libfontconfig1 \
    libfreetype6 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
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


# Copy dashboard-specific files (flat structure)
COPY 3DPlotly.py ./
# Requirements file is always copied as requirements.txt in build context
# (build script ensures it exists, even if empty)
COPY requirements.txt ./requirements.txt

# Install dashboard-specific requirements (skip if file is empty)
RUN if [ -s requirements.txt ]; then \
        python3 -m pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "No requirements to install (requirements.txt is empty)"; \
    fi


# Install additional requirements
RUN python3 -m pip install --no-cache-dir versioneer[toml] Cython pandas bokeh==3.8.0 dash dash-bootstrap-components dash_vtk vtk dash-vtk


# Fix permissions: Create bokehuser if it doesn't exist and add to www-data group
# This allows the dashboard to create sessions directories in /mnt/visus_datasets/upload/<UUID>/sessions
# IMPORTANT: Host directories at /mnt/visus_datasets/upload/<UUID> must have:
#   - Group ownership: www-data (or be group-writable)
#   - Permissions: 775 or 2775 (setgid) to allow group writes
#   Run on host: sudo chgrp -R www-data /mnt/visus_datasets/upload && sudo chmod -R g+w /mnt/visus_datasets/upload
USER root
RUN groupadd -f www-data && \
    (id -u plotlyuser >/dev/null 2>&1 || useradd -m -s /bin/bash -u 10001 plotlyuser) && \
    usermod -a -G www-data plotlyuser && \
    chown -R plotlyuser:plotlyuser /app
USER plotlyuser
# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8060

# Health check (if specified)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8060/ || exit 1

# Run dashboard entry point (match base image runtime user)
USER plotlyuser

CMD ["python3", "3DPlotly.py"]

