# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM visstore-plotly-dashboard-base:latest

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


# Copy dashboard-specific files (flat structure)
COPY 3DPlotly.py ./
#
COPY requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


#
# Install additional requirements
RUN python3 -m pip install --no-cache-dir versioneer[toml] Cython pandas bokeh==3.8.0 dash dash-bootstrap-components dash_vtk vtk dash-vtk


# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8050

# Health check (if specified)
#
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8050/health || exit 1


# Run dashboard entry point
CMD ["python3", "3DPlotly.py"]

