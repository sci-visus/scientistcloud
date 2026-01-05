# Getting Started with ScientistCloud Data Portal

This guide will help you get started with the ScientistCloud Data Portal, from authentication to uploading your first dataset.

## Prerequisites

- A ScientistCloud account (email address)
- `curl` command-line tool (for API examples)
- `jq` for JSON parsing (optional but recommended)
- Python 3.7+ (for Python examples)

## Step 1: Authentication

The first step is to authenticate and obtain an access token.

### Using curl

```bash
# Login and get token
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}' | \
     jq -r '.data.access_token')

# Verify token
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

Once authenticated, you can upload files to the portal.

### Basic Upload

```bash
curl -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@/path/to/your/file.nxs" \
     -F "dataset_name=My First Dataset" \
     -F "sensor=4D_NEXUS" \
     -F "convert=true" \
     -F "is_public=false"
```

### Upload Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `file` | Yes | File to upload | `@/path/to/file.nxs` |
| `dataset_name` | Yes | Name for the dataset | `"My Dataset"` |
| `sensor` | No | Sensor type | `4D_NEXUS`, `TIFF`, `OTHER` |
| `convert` | No | Convert to IDX format | `true` or `false` |
| `is_public` | No | Make dataset public | `true` or `false` |
| `folder` | No | Folder name for organization | `"CHESS_4D"` |
| `team_uuid` | No | Team UUID for sharing | `"team-uuid-here"` |
| `tags` | No | Comma-separated tags | `"tag1,tag2,tag3"` |

### Upload Response

```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Upload initiated",
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Step 3: Check Upload Status

After uploading, you can monitor the upload and conversion progress.

```bash
# Replace JOB_ID with the job_id from the upload response
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

View all your datasets:

```bash
curl -X GET "https://scientistcloud.com/portal/api/datasets" \
     -H "Authorization: Bearer $TOKEN" | jq
```

### Response

```json
{
  "success": true,
  "datasets": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My First Dataset",
      "sensor": "4D_NEXUS",
      "created_at": "2024-01-15T10:30:00Z",
      "status": "completed"
    }
  ]
}
```

## Step 5: Access Your Dataset

Once uploaded and processed, you can:

1. **View in Portal**: Navigate to `https://scientistcloud.com/portal/` and select your dataset
2. **Access via API**: Use the dataset UUID to get details and files
3. **Share with Team**: Use the team UUID to share with collaborators

## Using Ready-Made Scripts

For convenience, you can use the provided curl scripts. See the [Curl Scripts documentation](?page=curl-scripts) for details.

### Example: Quick Upload Script

```bash
# Download and customize the script
./curl_for_chess.sh -u your@email.com -f /path/to/file.nxs -n "Dataset Name"

# Or use defaults (edit script to set your defaults)
./curl_for_chess.sh
```

## Next Steps

- Read the [API Overview](?page=api) for complete API documentation
- Check out [Curl Scripts](?page=curl-scripts) for automation examples
- Explore [Python Examples](?page=python-examples) for programmatic access
- Review [Upload API](?page=api-upload) for advanced upload options

## Troubleshooting

### Authentication Failed

```bash
# Check if auth service is running
curl https://scientistcloud.com/api/auth/health

# Verify your email is correct
curl -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}'
```

### Upload Failed

```bash
# Check upload service health
curl https://scientistcloud.com/api/upload/health

# Verify file exists and is readable
ls -lh /path/to/your/file.nxs

# Check file size limits (contact admin if file is very large)
```

### Token Expired

Tokens expire after 24 hours. Simply login again to get a new token:

```bash
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}' | \
     jq -r '.data.access_token')
```

## Support

For additional help:
- Check the [API documentation](?page=api)
- Review example scripts in the [Curl Scripts](?page=curl-scripts) section
- Contact your system administrator

