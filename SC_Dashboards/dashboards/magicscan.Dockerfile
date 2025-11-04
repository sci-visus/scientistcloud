# Dockerfile template for ScientistCloud Dashboard
# Generated from dashboard.json configuration
# DO NOT EDIT MANUALLY - Regenerate using scripts/generate_dockerfile.sh

FROM magicscan-dashboard-base:latest

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
# Copy shared utility: msc_py.cpython-310-x86_64-linux-gnu.so
COPY SCLib_Dashboards/msc_py.cpython-310-x86_64-linux-gnu.so ./msc_py.cpython-310-x86_64-linux-gnu.so


# Copy dashboard-specific files (flat structure)
COPY magicscan.py ./
#
COPY requirements.txt ./requirements.txt


# Install dashboard-specific requirements
#
RUN python3 -m pip install --no-cache-dir -r requirements.txt


#
# Install additional requirements
RUN python3 -m pip install --no-cache-dir numpy>=1.21.0 scipy matplotlib scikit-image scikit-learn pandas>=2.2.3 h5py>=3.13.0 hdf5plugin>=5.0.0 panel>=1.5.0 holoviews==1.21.0 hvplot==0.11.2 datashader==0.17.0 colorcet==3.1.0 param==2.2.0 opencv-python-headless Pillow>=11.1.0 imageio>=2.37.0 tifffile albumentations==2.0.8 albucore==0.0.24 xarray zarr fastparquet>=2024.11.0 pyarrow>=19.0.1 fsspec>=2025.2.0 aiofiles==22.1.0 jupyterlab>=3.6.6 ipywidgets>=8.1.5 ipython notebook>=6.5.7 jupyter_bokeh==4.0.5 ipysheet==0.7.0 tornado>=6.4.2 aiohttp>=3.11.12 Flask>=3.0.3 requests>=2.32.3 tqdm>=4.67.1 click>=8.1.8 pyyaml>=6.0.2 python-dateutil>=2.9.0 pytz>=2025.1 packaging>=24.2 numba llvmlite joblib>=1.4.2 threadpoolctl>=3.5.0 psutil>=5.9.8 certifi>=2025.1.31 boto3


# Set environment variables from configuration


# Expose dashboard port
EXPOSE 8053

# Health check (if specified)
#
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8053/health || exit 1


# Run dashboard entry point
CMD ["sh", "-c", "python3 -m bokeh serve ./magicscan.py --allow-websocket-origin=${DOMAIN_NAME} --allow-websocket-origin=127.0.0.1 --allow-websocket-origin=0.0.0.0 --port=8053 --address=0.0.0.0 --use-xheaders --session-token-expiration=86400"]

