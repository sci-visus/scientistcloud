# Dashboard Management System - Implementation Plan

## Overview

This system provides a configuration-based approach to adding and managing dashboards in the ScientistCloud portal. Each dashboard is defined by a configuration file that specifies:
- Dashboard metadata (name, description, type)
- File locations (entry point, requirements)
- Port assignment
- Base image selection
- Dependencies and utilities

## Architecture

```
SC_Dashboards/
├── README.md
├── config/
│   ├── dashboard-registry.json          # Central registry of all dashboards
│   └── port-registry.json                # Port assignment registry
├── templates/
│   ├── Dockerfile.template              # Base Dockerfile template
│   └── nginx-config.template             # Nginx proxy template
├── scripts/
│   ├── add_dashboard.sh                 # Interactive script to add new dashboard
│   ├── generate_dockerfile.sh           # Generate Dockerfile from config
│   ├── generate_nginx_config.sh        # Generate nginx config from config
│   ├── register_dashboard.sh            # Register dashboard in registry
│   └── build_dashboard.sh               # Build dashboard Docker image
└── dashboards/
    ├── 3DPlotly/
    │   ├── dashboard.json                # Dashboard configuration
    │   ├── plotly_dashboard.py           # Entry point
    │   └── requirements.txt              # Python dependencies
    ├── 3DVTK/
    │   ├── dashboard.json
    │   └── ...
    └── ...
```

## Dashboard Configuration Schema

Each dashboard requires a `dashboard.json` file with the following structure:

```json
{
  "name": "3DPlotly",
  "display_name": "3D Plotly Dashboard",
  "description": "Interactive 3D visualization using Plotly and Dash",
  "version": "1.0.0",
  "type": "dash",  // dash, bokeh, jupyter, standalone
  "entry_point": "plotly_dashboard.py",
  "entry_point_type": "python",  // python, notebook, script
  "port": 8050,  // Auto-assigned if not specified
  "base_image": "plotly-dashboard-base",  // Base image name
  "base_image_tag": "latest",
  "requirements_file": "requirements.txt",
  "additional_requirements": [
    "dash-vtk",
    "vtk"
  ],
  "shared_utilities": [
    "mongo_connection.py",
    "utils_bokeh_mongodb.py"
  ],
  "environment_variables": {
    "SECRET_KEY": "${SECRET_KEY}",
    "DEPLOY_SERVER": "${DEPLOY_SERVER}",
    "DB_NAME": "${DB_NAME}",
    "MONGO_URL": "${MONGO_URL}"
  },
  "nginx_path": "/dashboard/plotly",  // URL path prefix
  "health_check_path": "/health",  // Optional health check endpoint
  "build_args": {
    "D_GIT_TOKEN": "${D_GIT_TOKEN}"
  },
  "volume_mounts": [],  // Optional volume mounts
  "exposed_ports": [8050],
  "depends_on": [],  // Service dependencies
  "enabled": true
}
```

## Port Management

Ports are automatically assigned from a reserved range:
- **Dashboard ports**: 8050-8999 (auto-increment)
- **Registry tracking**: `port-registry.json` tracks assignments

## Implementation Steps

### Step 1: Create Configuration Schema
- [x] Define JSON schema
- [ ] Create example configurations for existing dashboards
- [ ] Create validation script

### Step 2: Create Templates
- [ ] Dockerfile template with variables
- [ ] Nginx configuration template
- [ ] docker-compose template (optional)

### Step 3: Create Management Scripts
- [ ] `add_dashboard.sh` - Interactive dashboard addition
- [ ] `generate_dockerfile.sh` - Dockerfile generation
- [ ] `generate_nginx_config.sh` - Nginx config generation
- [ ] `register_dashboard.sh` - Registry management
- [ ] `build_dashboard.sh` - Build and test dashboard
- [ ] `list_dashboards.sh` - List all registered dashboards

### Step 4: Port Management
- [ ] Port registry system
- [ ] Auto-assignment logic
- [ ] Conflict detection

### Step 5: Base Image Standardization
- [ ] Create unified base image
- [ ] Migration guide for existing dashboards
- [ ] Build scripts for base images

### Step 6: Integration
- [ ] Update nginx configuration generation
- [ ] Update docker-compose generation
- [ ] Update portal dashboard manager
- [ ] Migration from old system

## Usage Example

### Adding a New Dashboard

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards
./scripts/add_dashboard.sh

# Interactive prompts:
# - Dashboard name: MyNewDashboard
# - Display name: My New Dashboard
# - Type: dash
# - Entry point: my_dashboard.py
# - Requirements file: requirements.txt
# - Base image: plotly-dashboard-base
# - Nginx path: /dashboard/mynew

# Script will:
# 1. Create dashboard directory
# 2. Generate dashboard.json
# 3. Assign port automatically
# 4. Register in dashboard-registry.json
# 5. Generate Dockerfile
# 6. Generate nginx configuration
# 7. Update docker-compose.yml (if needed)
```

### Building a Dashboard

```bash
./scripts/build_dashboard.sh 3DPlotly
```

### Listing Dashboards

```bash
./scripts/list_dashboards.sh
```

## Migration Path

1. **Phase 1**: Create configuration for existing dashboards
2. **Phase 2**: Generate Dockerfiles from templates
3. **Phase 3**: Generate nginx configs from templates
4. **Phase 4**: Test new system alongside old system
5. **Phase 5**: Migrate fully to new system
6. **Phase 6**: Remove old dashboard system

## Benefits

1. **Standardization**: All dashboards follow same structure
2. **Automation**: No manual Dockerfile/nginx editing
3. **Port Management**: Automatic port assignment
4. **Easy Updates**: Update config, regenerate files
5. **Documentation**: Config serves as documentation
6. **Validation**: Can validate configurations
7. **Testing**: Easier to test new dashboards

## Next Steps

1. Review and approve this plan
2. Create initial configuration files
3. Create templates
4. Create management scripts
5. Test with one existing dashboard
6. Migrate all dashboards
7. Update documentation


### Possible debugging.. 

<TBD>