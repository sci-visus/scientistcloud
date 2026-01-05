# API Overview

The ScientistCloud Data Portal provides a comprehensive REST API for programmatic access to all features.

## Base URLs

- **Main API**: `https://scientistcloud.com/api/`
- **Portal API**: `https://scientistcloud.com/portal/api/`
- **Authentication**: `https://scientistcloud.com/api/auth/`
- **Upload**: `https://scientistcloud.com/api/upload/`

## Authentication

All API endpoints (except login) require authentication using a Bearer token in the `Authorization` header:

```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```

See the [Authentication API documentation](?page=api-authentication) for details on obtaining tokens.

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login and get access token |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/logout` | POST | Logout and revoke token |
| `/api/auth/status` | GET | Check authentication status |
| `/api/auth/me` | GET | Get current user info |

### Upload Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload/upload` | POST | Upload a file |
| `/api/upload/initiate` | POST | Initiate chunked upload |
| `/api/upload/status/{job_id}` | GET | Get upload job status |
| `/api/upload/jobs` | GET | List user's upload jobs |

### Dataset Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/api/datasets` | GET | List user's datasets |
| `/portal/api/dataset-details` | GET | Get dataset details |
| `/portal/api/dataset-files` | GET | List dataset files |
| `/portal/api/dataset-status` | GET | Get dataset processing status |
| `/portal/api/update-dataset` | POST | Update dataset metadata |
| `/portal/api/delete-dataset` | POST | Delete a dataset |

### Folder Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/api/get-folders` | GET | List user's folders |

### Team Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/api/get-teams` | GET | List user's teams |
| `/portal/api/create-team` | POST | Create a new team |
| `/portal/api/update-team` | POST | Update team details |
| `/portal/api/share-dataset` | POST | Share dataset with team |

### Job Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portal/api/jobs` | GET | List user's jobs |
| `/portal/api/cancel-job` | POST | Cancel a job |
| `/portal/api/retry-conversion` | POST | Retry failed conversion |

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    // Response data
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

## Rate Limiting

API requests are rate-limited to prevent abuse. If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Pagination

List endpoints support pagination:

```bash
curl "https://scientistcloud.com/portal/api/datasets?page=1&limit=50" \
     -H "Authorization: Bearer $TOKEN"
```

## Filtering and Sorting

Many list endpoints support filtering and sorting:

```bash
# Filter by folder
curl "https://scientistcloud.com/portal/api/datasets?folder=CHESS_4D" \
     -H "Authorization: Bearer $TOKEN"

# Sort by date
curl "https://scientistcloud.com/portal/api/datasets?sort=created_at&order=desc" \
     -H "Authorization: Bearer $TOKEN"
```

## Examples

### Complete Workflow

```bash
# 1. Login
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')

# 2. Upload file
JOB_ID=$(curl -s -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@file.nxs" \
     -F "dataset_name=My Dataset" | \
     jq -r '.job_id')

# 3. Check status
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/upload/status/$JOB_ID" | jq

# 4. List datasets
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets" | jq
```

## Detailed Documentation

- [Authentication API](?page=api-authentication) - Complete authentication guide
- [Upload API](?page=api-upload) - File upload details and options
- [Datasets API](?page=api-datasets) - Dataset management operations

## SDKs and Libraries

- **Python**: See [Python Examples](?page=python-examples)
- **Curl**: See [Curl Scripts](?page=curl-scripts)
- **JavaScript**: Use fetch API with Bearer tokens

## Support

For API questions or issues:
- Check endpoint-specific documentation
- Review example scripts
- Contact your system administrator

