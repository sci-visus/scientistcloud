# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM bokeh-dashboard-base:latest

# Metadata
LABEL maintainer="ScientistCloud Team"
LABEL dashboard.name="magicscan"
LABEL dashboard.version="1.0.0"
LABEL dashboard.type="bokeh"

# Environment Variables
ENV PYTHONUNBUFFERED=True \
    TZ=America/Chicago \
    DASHBOARD_NAME=magicscan \
    DASHBOARD_PORT=8053

# Build arguments
ARG D_GIT_TOKEN
ARG INSTALL_HOME=/home/ViSOAR
ARG SC_DASHBOARDS_DIR=/app/SCLib_Dashboards

# Build arguments
ARG D_GIT_TOKEN
ARG DEPLOY_SERVER
ARG DOMAIN_NAME
ARG INSTALL_HOME=/home/ViSOAR

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
COPY /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/msc_py.cpython-310-x86_64-linux-gnu.so /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards/msc_py.cpython-310-x86_64-linux-gnu.so


# Copy dashboard-specific files
COPY magicscan/magicscan.py ./magicscan.py
#
COPY magicscan/requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


{{#if ADDITIONAL_REQUIREMENTS}}
# Install additional requirements
RUN python3 -m pip install --no-cache-dir numpy>=1.21.0 scipy matplotlib scikit-image scikit-learn pandas>=2.2.3 h5py>=3.13.0 hdf5plugin>=5.0.0 panel>=1.5.0 holoviews==1.21.0 hvplot==0.11.2 datashader==0.17.0 colorcet==3.1.0 param==2.2.0 opencv-python-headless Pillow>=11.1.0 imageio>=2.37.0 tifffile albumentations==2.0.8 albucore==0.0.24 xarray zarr fastparquet>=2024.11.0 pyarrow>=19.0.1 fsspec>=2025.2.0 aiofiles==22.1.0 jupyterlab>=3.6.6 ipywidgets>=8.1.5 ipython notebook>=6.5.7 jupyter_bokeh==4.0.5 ipysheet==0.7.0 tornado>=6.4.2 aiohttp>=3.11.12 Flask>=3.0.3 requests>=2.32.3 tqdm>=4.67.1 click>=8.1.8 pyyaml>=6.0.2 python-dateutil>=2.9.0 pytz>=2025.1 packaging>=24.2 numba llvmlite joblib>=1.4.2 threadpoolctl>=3.5.0 psutil>=5.9.8 certifi>=2025.1.31 boto3


# Set environment variables from configuration
{{#each ENVIRONMENT_VARIABLES}}
ENV {{@key}}={{this}}
{{/each}}

# Expose dashboard port
EXPOSE 8053

# Health check (if specified)
{{#if HEALTH_CHECK_PATH}}
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8053/health || exit 1


# Run dashboard entry point
# Generic Python application
#CMD ["python", "magicscan.py"]


CMD ["sh", "-c", "python3 -m panel serve ./magicscan.py --allow-websocket-origin=${DOMAIN_NAME} --port=8053 --address=0.0.0.0 --use-xheaders"]
