# API Overview

This page summarizes the current ScientistCloud API surface used by the portal.

## Base URL

- `https://scientistcloud.com`

## Core Services

### Authentication

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/auth/login` | POST | Login by email; returns access and refresh tokens |
| `/api/auth/refresh` | POST | Exchange refresh token for new tokens |
| `/api/auth/logout` | POST | Client-side logout flow; expects token in request body |
| `/api/auth/me` | GET | Current user profile |
| `/api/auth/status` | GET | Validate auth from bearer token/cookies |

### Upload Jobs

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/upload/upload` | POST | Main file upload endpoint |
| `/api/upload/upload-path` | POST | Upload by server-side file path |
| `/api/upload/status/{job_id}` | GET | Job progress/status |
| `/api/upload/jobs` | GET | Recent jobs for a user |
| `/api/upload/cancel/{job_id}` | POST | Cancel job |
| `/portal/api/jobs.php` | GET | Portal job list (user or admin); query `scope=active\|all`, `admin=1` for admins |
| `/portal/api/upload-status.php?job_id=` | GET | Portal proxy to upload status (live % and bytes) |
| `/portal/api/conversion-logs.php?dataset_uuid=` | GET | Conversion log tail for a dataset |

Portal UI: **Jobs** toolbar button or `index.php?jobs=1`. Admins: set `SC_PORTAL_ADMIN_EMAILS=you@example.com,other@example.com` in server env.
| `/api/upload/supported-sources` | GET | Supported upload source/sensor types |
| `/api/upload/limits` | GET | Upload limits and thresholds |

### Datasets (v1)

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/v1/datasets` | GET | List datasets with filters |
| `/api/v1/datasets/by-user` | GET | Datasets grouped as `my`, `shared`, `team` |
| `/api/v1/datasets/public` | GET | Public datasets |
| `/api/v1/datasets/public/{identifier}` | GET | Public dataset details |
| `/api/v1/datasets` | POST | Create dataset metadata record |
| `/api/v1/datasets/{identifier}` | GET | Dataset details (uuid/slug/id/name) |
| `/api/v1/datasets/{identifier}` | PUT | Update dataset metadata |
| `/api/v1/datasets/{identifier}` | DELETE | Delete dataset |
| `/api/v1/datasets/{identifier}/status` | GET | Dataset processing status |
| `/api/v1/datasets/{identifier}/convert` | POST | Queue conversion |

### Dataset Files (v1)

| Endpoint | Method |
|----------|--------|
| `/api/v1/datasets/{identifier}/files` | POST |
| `/api/v1/datasets/{identifier}/files` | GET |
| `/api/v1/datasets/{identifier}/files/{file_id}` | DELETE |
| `/api/v1/datasets/{identifier}/file-content` | GET |
| `/api/v1/datasets/{identifier}/file-serve` | GET |
| `/api/v1/datasets/{identifier}/settings` | GET |
| `/api/v1/datasets/{identifier}/settings` | PUT |
| `/api/v1/datasets/{identifier}/size` | GET |
| `/api/v1/user/storage` | GET |
| `/api/v1/teams/{team_uuid}/storage` | GET |

### S3 Runtime Helpers (new)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/datasets/s3/presign` | POST | Generate signed/public URL for S3-backed dataset assets |
| `/api/v1/datasets/s3/openvisus-resolved-idx` | POST | Generate resolved idx for OpenVisus runtime access |

## Auth Header

Most protected endpoints use:

```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Quick Workflow

```bash
# 1) Login
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}' | jq -r '.data.access_token')

# 2) Upload
curl -s -X POST "https://scientistcloud.com/api/upload/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/file.nxs" \
  -F "user_email=user@example.com" \
  -F "dataset_name=Example Dataset" \
  -F "sensor=4D_NEXUS"

# 3) List datasets by user
curl -s "https://scientistcloud.com/api/v1/datasets/by-user?user_email=user@example.com" | jq
```

## Related Pages

- [Authentication API](?page=api-authentication)
- [Upload API](?page=api-upload)
- [Datasets API](?page=api-datasets)
- [Curl Scripts](?page=curl-scripts)

