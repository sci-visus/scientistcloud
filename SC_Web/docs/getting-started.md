# Getting Started with ScientistCloud Data Portal

This guide covers the website first, then the API for automated uploads.

## Prerequisites

- A ScientistCloud account (for upload, sharing, and private data)
- Optional, for API examples: `curl`, `jq`, and Python 3.7+ with `requests`

## Using the Website

### Public Portal

Open [https://scientistcloud.com/portal/public/](https://scientistcloud.com/portal/public/) to browse public datasets. Select a dataset in the sidebar and pick a dashboard from the toolbar. No account is required.

### Account Portal

1. Open [https://scientistcloud.com/portal/index.php](https://scientistcloud.com/portal/index.php)
2. Sign in with Auth0 (Google, email/password, or another configured method)
3. Use **Upload** to add local files, a folder, a zip, Google Drive, S3, or a remote URL
4. Watch progress under **Jobs**
5. Click the dataset in the sidebar to open it in a dashboard

See [Dashboards](?page=dashboards), [Inspect S3](?page=inspect-s3), [Sharing and Teams](?page=sharing), and [Folders](?page=folders).

## Using the API

Website login (Auth0) is separate from API tokens. Scripts use `/api/auth/login` with your ScientistCloud account email.

### Step 1: Get a Token

```bash
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}' | \
     jq -r '.data.access_token')

echo "Token: ${TOKEN:0:20}..."
```

### Response

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 86400,
    "token_type": "Bearer",
    "user": {
      "email": "your@email.com",
      "name": "Your Name"
    }
  }
}
```

### Verify Authentication

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/status"
```

## Step 2: Upload Your First Dataset

Required form fields: `file`, `user_email`, `dataset_name`, and `sensor`.

```bash
curl -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@/path/to/your/file.nxs" \
     -F "user_email=your@email.com" \
     -F "dataset_name=My First Dataset" \
     -F "sensor=4D_NEXUS" \
     -F "convert=true" \
     -F "is_public=false"
```

### Upload Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `file` | Yes | File to upload | `@/path/to/file.nxs` |
| `user_email` | Yes | Owner email | `"your@email.com"` |
| `dataset_name` | Yes | Name for the dataset | `"My Dataset"` |
| `sensor` | Yes | Sensor type | `IDX`, `4D_NEXUS`, `TIFF`, `TIFF RGB`, `NETCDF`, `HDF5`, `RGB`, `MAPIR`, `ORNL_CHESS_STRAIN`, `OTHER`. [Contact us](mailto:support@visus.net) if your sensor is not in the list |
| `convert` | No | Convert to IDX format | `true` or `false` |
| `is_public` | No | Make dataset public | `true` or `false` |
| `folder` | No | Folder name for organization | `"CHESS_4D"` |
| `team_uuid` | No | Team UUID for sharing | `"team-uuid-here"` |
| `tags` | No | Comma-separated tags | `"tag1,tag2,tag3"` |

### Upload Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Upload initiated",
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Step 3: Check Upload Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/upload/status/JOB_ID" | jq
```

### Status Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percentage": 45,
  "message": "Converting dataset..."
}
```

## Step 4: List Your Datasets

```bash
curl -s "https://scientistcloud.com/api/v1/datasets/by-user?user_email=your@email.com" \
     -H "Authorization: Bearer $TOKEN" | jq
```

Response includes `datasets.my`, `datasets.shared`, `datasets.team`, and `counts`.

## Step 5: Access Your Dataset

Once uploaded and processed, you can:

1. **View in Portal**: Open `https://scientistcloud.com/portal/` and select your dataset
2. **Access via API**: Use the dataset UUID with the [Datasets API](?page=api-datasets)
3. **Share**: Use the portal **Share** button or the sharing API (see [Sharing and Teams](?page=sharing))

## Using Ready-Made Scripts

See [Curl Scripts](?page=curl-scripts) and [Python Examples](?page=python-examples).

```bash
./curl_for_chess.sh -u your@email.com -f /path/to/file.nxs -n "Dataset Name"
```

## Next Steps

- [Dashboards](?page=dashboards)
- [Inspect S3](?page=inspect-s3)
- [API Overview](?page=api)
- [Upload API](?page=api-upload)

## Troubleshooting

### Authentication Failed

```bash
# Check if the auth service is running (trailing slash required)
curl https://scientistcloud.com/api/health/

# Confirm login for your account email
curl -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}'
```

The website uses Auth0. If the portal login page fails, use **Sign In** on `https://scientistcloud.com/portal/index.php` rather than the API token flow.

### Upload Failed

```bash
# Check upload service health (trailing slash required)
curl https://scientistcloud.com/api/upload-health/

# Check file exists and is readable
ls -lh /path/to/your/file.nxs

# Check size limits
curl https://scientistcloud.com/api/upload/limits
```

### Token Expired

Access tokens expire after 24 hours. Log in again:

```bash
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}' | \
     jq -r '.data.access_token')
```

## Support

- [API Overview](?page=api)
- [Curl Scripts](?page=curl-scripts)
- Contact [support@visus.net](mailto:support@visus.net)
