# ScientistCloud Data Portal Documentation

Welcome to the ScientistCloud Data Portal documentation. These pages cover the public portal, the signed-in account portal, dashboards, and the REST API.

## Overview

ScientistCloud is a web platform for managing, uploading, and visualizing scientific datasets. It provides:

- **Web interface**: Browse, upload, organize, share, and visualize datasets
- **REST API**: Programmatic access for ingest and dataset management
- **Command-line tools**: Curl scripts for automated uploads
- **Python examples**: `requests`-based examples (no separate pip SDK)

## Public Portal vs Account-Based Portal

The ScientistCloud Data Portal offers two access modes.

### Public Portal

**Location:** `https://scientistcloud.com/portal/public/`

Anyone can browse and view publicly available datasets without creating an account.

**Features:**

- Browse datasets marked as public
- View dataset details and metadata
- Use available dashboards for visualization
- Download datasets only if they are marked as publicly downloadable
- Access this documentation

**Limitations:**

- Cannot upload datasets
- Cannot edit or delete datasets
- Cannot view private datasets
- Cannot manage teams or sharing

To upload data, sign in or create an account to use the account-based portal.

### Account-Based Portal

**Location:** `https://scientistcloud.com/portal/index.php`

Registered users get the public portal features plus:

- Upload and manage your own datasets
- Edit dataset metadata (name, tags, description, folder)
- Delete your datasets
- Share datasets with other users or teams
- Create and manage teams
- Set dataset visibility (public/private)
- Control download permissions
- Inspect and link S3 data
- Retry failed conversions
- View job status and processing logs

**Access:** The website uses Auth0. Sign in with Google, email/password, or other configured methods. API scripts use a separate JWT login (see [Authentication API](?page=api-authentication)).

### Choosing the Right Portal

- Use the **Public Portal** to browse and view public datasets
- Use the **Account-Based Portal** to upload data, manage datasets, or collaborate with teams

Both portals share the same visualization dashboards and supported dataset formats.

## Quick Links

### Using the Portal

- [Getting Started Guide](?page=getting-started) - Sign in, upload, and view data
- [Dashboards](?page=dashboards) - OpenVisus, Plotly, VTK, 4D, MagicScan, Dark Matter, CHESS
- [Inspect S3](?page=inspect-s3) - Browse object storage and link datasets
- [Sharing and Teams](?page=sharing) - Share with people, teams, and dashboard links
- [Folders](?page=folders) - Organize datasets in the sidebar

### API Documentation

- [API Overview](?page=api) - Endpoints and base URLs
- [Authentication API](?page=api-authentication) - JWT tokens for scripts
- [Upload API](?page=api-upload) - Upload files and manage jobs
- [Datasets API](?page=api-datasets) - Datasets, folders, and teams

### Examples and Tools

- [Curl Scripts](?page=curl-scripts) - Command-line uploads
- [Python Examples](?page=python-examples) - Python `requests` examples

## Base URL

API services:

```
https://scientistcloud.com/api/
```

Portal PHP endpoints (session cookie from the website):

```
https://scientistcloud.com/portal/api/
```

## Authentication

**Website:** Sign in at `https://scientistcloud.com/portal/index.php` with Auth0.

**API / curl / Python:** Exchange your ScientistCloud account email for a JWT, then send it as `Authorization: Bearer`.

See the [Authentication API documentation](?page=api-authentication).

## Common Use Cases

### Upload a File

```bash
# 1. Get authentication token
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}' | \
     jq -r '.data.access_token')

# 2. Upload file
curl -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@/path/to/file.nxs" \
     -F "user_email=your@email.com" \
     -F "dataset_name=My Dataset" \
     -F "sensor=4D_NEXUS"
```

### List Your Datasets

```bash
curl -s "https://scientistcloud.com/api/v1/datasets/by-user?user_email=your@email.com" \
     -H "Authorization: Bearer $TOKEN" | jq
```

### Check Upload Status

```bash
curl -X GET "https://scientistcloud.com/api/upload/status/JOB_ID" \
     -H "Authorization: Bearer $TOKEN" | jq
```

## Need Help?

- Check the [Getting Started Guide](?page=getting-started)
- Review the [API Overview](?page=api)
- See [Curl Scripts](?page=curl-scripts) and [Python Examples](?page=python-examples)

## API Status

Trailing slashes are required on these health URLs:

```bash
# Authentication service
curl https://scientistcloud.com/api/health/

# Upload service
curl https://scientistcloud.com/api/upload-health/
```

Utility checks that do not require a token:

```bash
curl https://scientistcloud.com/api/upload/limits
curl https://scientistcloud.com/api/upload/supported-sources
```
