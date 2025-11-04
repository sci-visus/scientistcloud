# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM visstore-4d-dashboard-base:latest

# Metadata
LABEL maintainer="ScientistCloud Team"
LABEL dashboard.name="4d_dashboard"
LABEL dashboard.version="1.0.0"
LABEL dashboard.type="bokeh"

# Environment Variables
ENV PYTHONUNBUFFERED=True \
    TZ=America/Chicago \
    DASHBOARD_NAME=4d_dashboard \
    DASHBOARD_PORT=8052

# Build arguments
ARG D_GIT_TOKEN
ARG INSTALL_HOME=/home/ViSOAR
ARG SC_DASHBOARDS_DIR=/app/SCLib_Dashboards

# Build arguments
ARG DEPLOY_SERVER
ARG DOMAIN_NAME

# Environment Variables (inherited from base image)
ENV DEPLOY_SERVER=${DEPLOY_SERVER}
ENV DOMAIN_NAME=${DOMAIN_NAME}

# Echo build information
RUN echo "DEPLOY SERVER: ${DEPLOY_SERVER}"

# Set working directory
WORKDIR ${INSTALL_HOME}/dataportal

# Copy shared dashboard utilities from SCLib_Dashboards
# These are mounted/copied from scientistCloudLib/SCLib_Dashboards
COPY COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/mongo_connection.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/mongo_connection.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_mongodb.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_mongodb.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_dashboard.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_dashboard.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_auth.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_auth.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_param.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_param.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/process_4dnexus.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/process_4dnexus.py


# Copy dashboard-specific files
COPY 4d_dashboard/4d_dashboard.py ./4d_dashboard.py
#
COPY 4d_dashboard/requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


{{#if ADDITIONAL_REQUIREMENTS}}
# Install additional requirements
RUN python3 -m pip install --no-cache-dir bokeh==3.8.0 panel jupyter boto3 scikit-image bokeh[server] tornado>=6.1 markupsafe>=2.0 six>=1.16 packaging>=21.0 pyyaml>=5.4 python-dateutil>=2.8 babel>=2.9 click>=8.0 pillow>=8.0


# Set environment variables from configuration
{{#each ENVIRONMENT_VARIABLES}}
ENV {{@key}}={{this}}
{{/each}}

# Expose dashboard port
EXPOSE 8052

# Health check (if specified)
{{#if HEALTH_CHECK_PATH}}
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8052/health || exit 1


# Run dashboard entry point
# Generic Python application
#CMD ["python", "4d_dashboard.py"]
CMD ["sh", "-c", "cd /app && python3 -m bokeh serve ./4d_dashboard.py --allow-websocket-origin=${DOMAIN_NAME} --port=8052 --address=0.0.0.0 --use-xheaders --session-token-expiration=86400"]


