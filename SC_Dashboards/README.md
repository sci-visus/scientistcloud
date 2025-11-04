# ScientistCloud Dashboard Management System

## Overview

This system provides a configuration-based approach to adding and managing dashboards in the ScientistCloud portal. Each dashboard is defined by a `dashboard.json` configuration file that specifies all the necessary information for building, deploying, and accessing the dashboard.

## Quick Start

### Initializing a Dashboard (Recommended)

Once you have your `.py` and `.json` files, initialize everything:

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards
./scripts/init_dashboard.sh <dashboard_name>
```

**Options:**
- `--overwrite` - Overwrite existing Dockerfile and nginx config
- `--build` - Build Docker image after generating files
- `--skip-build` - Skip Docker image build (default)

**Examples:**
```bash
# Generate files only (skip if exist)
./scripts/init_dashboard.sh 3DPlotly

# Overwrite existing files
./scripts/init_dashboard.sh 3DPlotly --overwrite

# Generate files and build image
./scripts/init_dashboard.sh 3DPlotly --build

# Overwrite and build
./scripts/init_dashboard.sh 3DPlotly --overwrite --build
```

This script will:
1. Generate Dockerfile from template
2. Generate nginx configuration
3. Optionally build Docker image
4. Export dashboard list for portal
5. Show docker-compose integration instructions

### Generating Docker Compose Entries

To generate docker-compose service entries for all dashboards:

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Dashboards
./scripts/generate_docker_compose.sh --output ../SC_Docker/dashboards-docker-compose.yml
```

Then integrate into your main `docker-compose.yml` or use multiple files:

```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker
docker-compose -f docker-compose.yml -f dashboards-docker-compose.yml up -d
```

**Main docker-compose file location:**
`/Users/amygooch/GIT/ScientistCloud_2.0/scientistcloud/SC_Docker/docker-compose.yml`

### Adding a New Dashboard

```bash
./scripts/add_dashboard.sh
```

Follow the interactive prompts to create your dashboard configuration.

### Building a Dashboard

```bash
./scripts/build_dashboard.sh <dashboard_name>
```

### Listing Dashboards

```bash
./scripts/list_dashboards.sh
```

## Directory Structure

**Flat structure only** - simple and easy to maintain:

```
SC_Dashboards/
├── README.md
├── DASHBOARD_MANAGEMENT_PLAN.md
├── config/
│   ├── dashboard-registry.json      # Central registry of all dashboards
│   ├── port-registry.json           # Port assignment registry
│   └── dashboards-list.json         # Generated list for portal consumption
├── templates/
│   ├── Dockerfile.template          # Base Dockerfile template
│   └── nginx-config.template        # Nginx proxy template
├── scripts/
│   ├── add_dashboard.sh             # Interactive dashboard addition
│   ├── generate_dockerfile.sh      # Generate Dockerfile from config
│   ├── generate_nginx_config.sh    # Generate nginx config
│   ├── register_dashboard.sh       # Register dashboard in registry
│   ├── build_dashboard.sh          # Build dashboard Docker image
│   ├── list_dashboards.sh          # List all registered dashboards
│   └── export_dashboard_list.sh    # Export dashboard list for portal
└── dashboards/
    ├── 3DPlotly.json                # Dashboard configuration
    ├── 3DPlotly.py                  # Entry point
    ├── 3DPlotly_requirements.txt    # Python dependencies
    ├── 3DPlotly.Dockerfile          # Generated Dockerfile
    └── ...
```

All files for a dashboard are in the `dashboards/` directory with the pattern `{name}.*`.

## Dashboard Configuration Schema

Each dashboard requires a `{dashboard_name}.json` file in the `dashboards/` directory.

See `DASHBOARD_MANAGEMENT_PLAN.md` for full schema documentation.

Required fields:
- `name`: Dashboard identifier (e.g., "3DPlotly")
- `display_name`: Human-readable name
- `type`: Dashboard type (dash, bokeh, jupyter, standalone)
- `entry_point`: Main Python file or notebook (e.g., `3DPlotly.py`)
- `port`: Dashboard port (auto-assigned if not specified)
- `base_image`: Base Docker image
- `nginx_path`: URL path prefix (e.g., "/dashboard/plotly")

The `entry_point` should match the dashboard name (e.g., `3DPlotly.py`), and `requirements_file` should be `{name}_requirements.txt`.

## Integration with Portal

The portal automatically discovers dashboards by:

1. **API Endpoint**: `/portal/api/dashboards.php` - Returns list of available dashboards
2. **Frontend**: `viewer-manager.js` loads dashboards from API and populates the viewer selector
3. **Backend**: `dashboard_manager.php` fetches dashboards from registry

### Exporting Dashboard List

To make dashboards available to the portal, run:

```bash
./scripts/export_dashboard_list.sh
```

This generates `config/dashboards-list.json` which the portal API reads.

## Port Management

Ports are automatically assigned from range 8050-8999. The `port-registry.json` tracks all assignments to prevent conflicts.

## Next Steps

1. Create `dashboard.json` files for existing dashboards
2. Generate Dockerfiles for all dashboards
3. Generate nginx configurations
4. Update docker-compose.yml to include new services
5. Test dashboard discovery and loading
6. Migrate from old dashboard system

