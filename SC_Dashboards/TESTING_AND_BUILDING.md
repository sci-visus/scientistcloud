# Testing and Building Dashboards

This guide explains how to test and build the new dashboard system.

## Quick Start

### Step 1: Initialize All Dashboards

First, make sure all dashboards have their Dockerfiles generated:

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards

# Initialize all dashboards (generates Dockerfiles and nginx configs)
for dashboard in 3DPlotly 3DVTK 4d_dashboard magicscan OpenVisusSlice; do
    ./scripts/init_dashboard.sh $dashboard
done
```

Or initialize one at a time:

```bash
./scripts/init_dashboard.sh 3DPlotly
```

### Step 2: Build a Single Dashboard

Build a dashboard Docker image:

```bash
# Build a single dashboard
./scripts/build_dashboard.sh <dashboard_name>

# Example: Build 3DPlotly
./scripts/build_dashboard.sh 3DPlotly

# Build with a specific tag
./scripts/build_dashboard.sh 3DPlotly v1.0
```

**What this does:**
- Creates a temporary build context
- Copies dashboard files (`.py`, `.json`, `requirements.txt`)
- Copies shared utilities from `SCLib_Dashboards`
- Copies the Dockerfile
- Builds the Docker image: `<dashboard_name>_dashboard:latest`

### Step 3: Test a Dashboard Locally

Run a dashboard container to test it:

```bash
# Run a dashboard container
docker run -d \
  --name test-3dplotly \
  -p 8050:8050 \
  -e DEPLOY_SERVER=https://scientistcloud.com \
  -e DOMAIN_NAME=scientistcloud.com \
  -e SECRET_KEY=test-secret \
  -e DB_NAME=test_db \
  -e MONGO_URL=mongodb://localhost:27017 \
  3dplotly_dashboard:latest

# Check if it's running
docker ps | grep test-3dplotly

# View logs
docker logs test-3dplotly

# Test the dashboard
curl http://localhost:8050/health

# Stop and remove test container
docker stop test-3dplotly
docker rm test-3dplotly
```

### Step 4: Build All Dashboards

Build all enabled dashboards:

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards

# Build all registered dashboards
for dashboard in 3DPlotly 3DVTK 4d_dashboard magicscan OpenVisusSlice; do
    echo "Building $dashboard..."
    ./scripts/build_dashboard.sh $dashboard
done
```

Or use the list from the registry:

```bash
# Get list of enabled dashboards from registry
jq -r '.dashboards | to_entries[] | select(.value.enabled == true) | .key' \
   config/dashboard-registry.json | \
   while read dashboard; do
       echo "Building $dashboard..."
       ./scripts/build_dashboard.sh "$dashboard"
   done
```

### Step 5: Integrate with Docker Compose

Generate docker-compose entries and integrate:

```bash
# Generate docker-compose entries
./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml

# Start all services (portal + dashboards)
cd ../SC_Docker
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml up -d

# Or build and start
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml up -d --build

# Check status
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml ps

# View logs
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml logs -f dashboard_3dplotly
```

### Step 6: Test Dashboards via Nginx

Once nginx configs are generated and integrated:

```bash
# Test dashboard endpoints
curl https://scientistcloud.com/dashboard/plotly/health
curl https://scientistcloud.com/dashboard/vtk/health
curl https://scientistcloud.com/dashboard/4d/health
curl https://scientistcloud.com/dashboard/magicscan/health
curl https://scientistcloud.com/dashboard/openvisus/health
```

## Detailed Workflow

### Complete Dashboard Setup

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards

# 1. Initialize dashboard (generates Dockerfile, nginx config)
./scripts/init_dashboard.sh 3DPlotly

# 2. Build the Docker image
./scripts/build_dashboard.sh 3DPlotly

# 3. Test locally (optional)
docker run -d --name test-3dplotly -p 8050:8050 \
  -e DEPLOY_SERVER=https://scientistcloud.com \
  -e DOMAIN_NAME=scientistcloud.com \
  -e SECRET_KEY=test \
  -e DB_NAME=test \
  -e MONGO_URL=mongodb://localhost:27017 \
  3dplotly_dashboard:latest

# 4. Check logs
docker logs -f test-3dplotly

# 5. Test health endpoint
curl http://localhost:8050/health

# 6. Clean up test
docker stop test-3dplotly && docker rm test-3dplotly

# 7. Generate docker-compose entries
./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml

# 8. Start with docker-compose
cd ../SC_Docker
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml up -d dashboard_3dplotly
```

## Troubleshooting

### Build Issues

**Problem: Base image not found**
```bash
# Build the base image first
# Check what base image is needed in dashboard.json
jq -r '.base_image' dashboards/3DPlotly.json

# Base images are defined in VisusDataPortalPrivate/Docker/docker-compose.yaml
# They should be built with the profile: base-images
```

**Problem: Shared utilities not found**
```bash
# Check if SCLib_Dashboards exists
ls -la /Users/amygooch/GIT/ScientistCloud_2.0/scientistCloudLib/SCLib_Dashboards

# If missing, create it or update the path in generate_dockerfile.sh
```

**Problem: Requirements file not found**
```bash
# Check if requirements file exists
ls -la dashboards/3DPlotly_requirements.txt

# If missing, create it or update dashboard.json
```

### Runtime Issues

**Problem: Container exits immediately**
```bash
# Check logs
docker logs <container_name>

# Common issues:
# - Missing environment variables
# - Port conflicts
# - Missing dependencies
```

**Problem: Dashboard not accessible**
```bash
# Check if container is running
docker ps | grep <dashboard_name>

# Check port mapping
docker port <container_name>

# Check nginx configuration
cat ../SC_Docker/nginx/conf.d/<dashboard_name>_dashboard.conf

# Test direct connection (bypass nginx)
curl http://localhost:<port>/health
```

### Testing Checklist

- [ ] Dockerfile generated successfully
- [ ] Docker image builds without errors
- [ ] Container starts and stays running
- [ ] Health endpoint responds (if configured)
- [ ] Dashboard accessible via nginx (if configured)
- [ ] Dashboard loads in browser
- [ ] No errors in container logs
- [ ] Environment variables set correctly

## Environment Variables

Required environment variables for dashboards:

```bash
DEPLOY_SERVER=https://scientistcloud.com
DOMAIN_NAME=scientistcloud.com
SECRET_KEY=<your-secret-key>
DB_NAME=<database-name>
MONGO_URL=<mongodb-connection-string>
```

Optional (from dashboard.json):
- Additional environment variables can be configured in `dashboard.json` under `environment_variables`

## Port Assignments

Dashboard ports are managed in `config/port-registry.json`:

- **3DPlotly**: 8050
- **3DVTK**: 8051
- **4D_Dashboard**: 8052
- **Magicscan**: 8053
- **OpenVisusSlice**: 8054

Port range: 8050-8999

## Next Steps

After building and testing:

1. **Integrate nginx configs**: Ensure generated nginx configs are included in main nginx configuration
2. **Update docker-compose**: Add dashboard services to main docker-compose.yml or use separate file
3. **Deploy**: Push images to registry or deploy to production
4. **Monitor**: Set up health checks and monitoring


