# ScientistCloud Data Portal Documentation

Welcome to the ScientistCloud Data Portal documentation! This documentation provides comprehensive guides and examples for using the ScientistCloud API and tools.

## Overview

The ScientistCloud Data Portal is a web-based platform for managing, uploading, and visualizing scientific datasets. It provides:

## Public Portal vs Account-Based Portal

The ScientistCloud Data Portal offers two access modes:

### Public Portal

**Location:** `https://scientistcloud.com/portal/public/`

The Public Portal allows anyone to browse and view publicly available datasets without creating an account or logging in.

**Features:**
- Browse all datasets marked as public
- View dataset details and metadata
- Use all available dashboards for visualization
- Download datasets (only if marked as publicly downloadable)
- Access documentation

**Limitations:**
- Cannot upload datasets
- Cannot edit or delete datasets
- Cannot view private datasets
- Cannot manage teams or sharing

**To Upload Data:** Users must sign in or create an account to access the full Account-Based Portal.

### Account-Based Portal

**Location:** `https://scientistcloud.com/portal/index.php`

The Account-Based Portal provides full functionality for registered users.

**Features:**
- All Public Portal features, plus:
- Upload and manage your own datasets
- Edit dataset metadata (name, tags, description, etc.)
- Delete your datasets
- Share datasets with other users or teams
- Create and manage teams
- Set dataset visibility (public/private)
- Control download permissions
- Retry failed conversions
- View job status and processing logs

**Access:** Requires authentication via Auth0. Users can sign in with Google, email/password, or other configured authentication methods.

### Choosing the Right Portal

- **Use the Public Portal** if you only need to browse and view publicly available datasets
- **Use the Account-Based Portal** if you need to upload data, manage datasets, or collaborate with teams

Both portals share the same visualization dashboards and support the same dataset formats.

- **Web Interface**: User-friendly dashboard for managing datasets
- **REST API**: Programmatic access to all portal features
- **Command-Line Tools**: Scripts for automated uploads and dataset management
- **Python SDK**: Python libraries for integration

## Quick Links

### Getting Started
- [Getting Started Guide](?page=getting-started) - Learn how to set up and use the portal
- [API Overview](?page=api) - Understand the API structure and endpoints

### API Documentation
- [Authentication API](?page=api-authentication) - How to authenticate and get tokens
- [Upload API](?page=api-upload) - Upload files and manage uploads
- [Datasets API](?page=api-datasets) - Manage datasets, folders, and teams

### Examples and Tools
- [Curl Scripts](?page=curl-scripts) - Command-line scripts for uploads and automation
- [Python Examples](?page=python-examples) - Python code examples and SDK usage

## Base URL

All API endpoints are available at:

```
https://scientistcloud.com/api/
```

For portal-specific endpoints:

```
https://scientistcloud.com/portal/api/
```

## Authentication

The ScientistCloud API uses JWT (JSON Web Token) authentication. You'll need to:

1. **Login** to get an access token
2. **Include the token** in the `Authorization` header for all API requests
3. **Refresh the token** when it expires

See the [Authentication API documentation](?page=api-authentication) for detailed instructions.

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
     -F "dataset_name=My Dataset" \
     -F "sensor=4D_NEXUS"
```

### List Your Datasets

```bash
curl -X GET "https://scientistcloud.com/portal/api/datasets" \
     -H "Authorization: Bearer $TOKEN" | jq
```

### Check Upload Status

```bash
curl -X GET "https://scientistcloud.com/api/upload/status/JOB_ID" \
     -H "Authorization: Bearer $TOKEN" | jq
```

## Need Help?

- Check the [Getting Started Guide](?page=getting-started) for setup instructions
- Review the [API documentation](?page=api) for endpoint details
- See [Curl Scripts](?page=curl-scripts) for ready-to-use automation scripts
- Explore [Python Examples](?page=python-examples) for programmatic access

## API Status

You can check the health of API services:

```bash
# Check authentication service
curl https://scientistcloud.com/api/auth/health

# Check upload service
curl https://scientistcloud.com/api/upload/health
```

