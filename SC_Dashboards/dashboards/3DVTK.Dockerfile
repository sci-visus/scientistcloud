# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM vtk-dashboard-base:latest

# Metadata
LABEL maintainer="ScientistCloud Team"
LABEL dashboard.name="3DVTK"
LABEL dashboard.version="1.0.0"
LABEL dashboard.type="dash"

# Build arguments
ARG DEPLOY_SERVER
ARG DOMAIN_NAME

# Environment Variables (inherited from base image)
ENV DEPLOY_SERVER=${DEPLOY_SERVER}
ENV DOMAIN_NAME=${DOMAIN_NAME}

# Environment variables for headless VTK/PyVista rendering
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=offscreen
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330

# Environment Variables
ENV PYTHONUNBUFFERED=True \
    TZ=America/Chicago \
    DASHBOARD_NAME=3DVTK \
    DASHBOARD_PORT=8051

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
COPY 3DVTK/3DVTK.py ./3DVTK.py
#

RUN apt-get update && apt-get install -y --no-install-recommends \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxtst6 \
        libxi6 \
        libxrandr2 \
        libxss1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxfixes3 \
        libxinerama1 \
        libxmu6 \
        libxpm4 \
        libxaw7 \
        libxft2 \
        libfontconfig1 \
        libfreetype6 \
        libgl1-mesa-dri \
        libglu1-mesa \
        libglib2.0-0 \
        libgthread-2.0-0 \
        libgtk-3-0 \
        libgdk-pixbuf-xlib-2.0-0 \
        libcairo-gobject2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libpangoft2-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY 3DVTK/requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt
# Install PyVista with Jupyter support for 3D volume visualization
RUN python3 -m pip install --no-cache-dir "pyvista[jupyter]"


{{#if ADDITIONAL_REQUIREMENTS}}
# Install additional requirements
RUN python3 -m pip install --no-cache-dir pyvista>=0.44.0 vtk>=9.3.0 panel>=1.3.0 numpy>=1.21.0 matplotlib>=3.5.0


# Set environment variables from configuration
{{#each ENVIRONMENT_VARIABLES}}
ENV {{@key}}={{this}}
{{/each}}

# Expose dashboard port
EXPOSE 8051

# Health check (if specified)
{{#if HEALTH_CHECK_PATH}}
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8051/health || exit 1


# Run dashboard entry point
# Generic Python application
#CMD ["python", "3DVTK.py"]

CMD ["sh", "-c", "python3 -m bokeh serve ./3DVTK.py --port=8051 --address=0.0.0.0 --allow-websocket-origin=${DOMAIN_NAME} --session-token-expiration=86400"]
 