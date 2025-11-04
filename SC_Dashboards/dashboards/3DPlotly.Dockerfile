# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM plotly-dashboard-base:latest

# Metadata
LABEL maintainer="ScientistCloud Team"
LABEL dashboard.name="3DPlotly"
LABEL dashboard.version="1.0.0"
LABEL dashboard.type="dash"

# Environment Variables
ENV PYTHONUNBUFFERED=True \
    TZ=America/Chicago \
    DASHBOARD_NAME=3DPlotly \
    DASHBOARD_PORT=8050

# Build arguments
ARG D_GIT_TOKEN
ARG INSTALL_HOME=/home/ViSOAR
ARG SC_DASHBOARDS_DIR=/app/SCLib_Dashboards

# Set working directory
WORKDIR ${INSTALL_HOME}/dataportal

# Copy shared dashboard utilities from SCLib_Dashboards
# These are mounted/copied from scientistCloudLib/SCLib_Dashboards
COPY COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/mongo_connection.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/mongo_connection.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_mongodb.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_mongodb.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_dashboard.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_dashboard.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_auth.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_auth.py
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_param.py /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/utils_bokeh_param.py


# Copy dashboard-specific files
COPY 3DPlotly/3DPlotly.py ./3DPlotly.py
#
COPY 3DPlotly/requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


{{#if ADDITIONAL_REQUIREMENTS}}
# Install additional requirements
RUN python3 -m pip install --no-cache-dir versioneer[toml] Cython pandas bokeh==3.8.0 dash dash-bootstrap-components dash_vtk vtk dash-vtk


# Set environment variables from configuration
{{#each ENVIRONMENT_VARIABLES}}
ENV {{@key}}={{this}}
{{/each}}

# Expose dashboard port
EXPOSE 8050

# Health check (if specified)
{{#if HEALTH_CHECK_PATH}}
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8050/health || exit 1


# Run dashboard entry point
# Generic Python application
CMD ["python3", "3DPlotly.py"]


