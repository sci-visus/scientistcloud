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
COPY 3DVTK.py ./
#
COPY requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


#
# Install additional requirements
RUN python3 -m pip install --no-cache-dir pyvista>=0.44.0 vtk>=9.3.0 panel>=1.3.0 numpy>=1.21.0 matplotlib>=3.5.0


# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8051

# Health check (if specified)
#
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8051/health || exit 1


# Run dashboard entry point
CMD ["sh", "-c", "python3 -m bokeh serve ./3DVTK.py --allow-websocket-origin=${DOMAIN_NAME} --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=8051 --address=0.0.0.0 --use-xheaders --session-token-expiration=86400"]

