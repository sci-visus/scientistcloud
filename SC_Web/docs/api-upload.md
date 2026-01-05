# Upload API

The Upload API allows you to upload files to the ScientistCloud Data Portal and manage upload jobs.

## Overview

The upload process:

1. **Authenticate** - Get an access token
2. **Upload File** - Upload file with metadata
3. **Monitor Progress** - Check upload and conversion status
4. **Access Dataset** - Use the dataset UUID to access your data

## Upload File

### POST `/api/upload/upload`

Upload a file to create a new dataset.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@/path/to/file.nxs" \
     -F "dataset_name=My Dataset" \
     -F "sensor=4D_NEXUS" \
     -F "convert=true" \
     -F "is_public=false" \
     -F "folder=CHESS_4D" \
     -F "tags=nexus,4d,chess"
```

**Form Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `file` | Yes | File | File to upload |
| `dataset_name` | Yes | String | Name for the dataset |
| `user_email` | No | String | User email (uses token if not provided) |
| `sensor` | No | String | Sensor type: `4D_NEXUS`, `TIFF`, `OTHER` |
| `convert` | No | Boolean | Convert to IDX format (default: `true`) |
| `is_public` | No | Boolean | Make dataset public (default: `false`) |
| `folder` | No | String | Folder name for organization |
| `team_uuid` | No | String | Team UUID for sharing |
| `tags` | No | String | Comma-separated tags |
| `dataset_identifier` | No | String | Custom dataset identifier |
| `add_to_existing` | No | Boolean | Add to existing dataset |

**Response:**

```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Upload initiated"
}
```

## Upload Status

### GET `/api/upload/status/{job_id}`

Get the status of an upload job.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/upload/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percentage": 45,
  "message": "Converting dataset...",
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Values:**

- `pending` - Upload queued
- `uploading` - File being uploaded
- `processing` - File being converted
- `completed` - Upload and conversion complete
- `failed` - Upload or conversion failed
- `cancelled` - Job cancelled

## List Upload Jobs

### GET `/api/upload/jobs`

List all upload jobs for the authenticated user.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/upload/jobs"
```

**Response:**

```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "dataset_name": "My Dataset",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "progress_percentage": 100
    }
  ]
}
```

## Initiate Chunked Upload

### POST `/api/upload/initiate`

For large files, initiate a chunked upload session.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/api/upload/initiate" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_name": "Large Dataset",
       "file_size": 10737418240,
       "file_name": "large_file.nxs",
       "sensor": "4D_NEXUS"
     }'
```

**Response:**

```json
{
  "success": true,
  "upload_id": "upload_abc123",
  "chunk_size": 10485760,
  "total_chunks": 1024
}
```

## Complete Example

```bash
#!/bin/bash

# 1. Authenticate
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')

# 2. Upload file
echo "Uploading file..."
RESPONSE=$(curl -s -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@/path/to/file.nxs" \
     -F "dataset_name=My Dataset" \
     -F "sensor=4D_NEXUS" \
     -F "convert=true")

JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
DATASET_UUID=$(echo "$RESPONSE" | jq -r '.dataset_uuid')

echo "Upload started! Job ID: $JOB_ID"
echo "Dataset UUID: $DATASET_UUID"

# 3. Monitor progress
echo "Monitoring upload progress..."
while true; do
    STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" \
         "https://scientistcloud.com/api/upload/status/$JOB_ID")
    
    PROGRESS=$(echo "$STATUS" | jq -r '.progress_percentage')
    JOB_STATUS=$(echo "$STATUS" | jq -r '.status')
    
    echo "Status: $JOB_STATUS ($PROGRESS%)"
    
    if [ "$JOB_STATUS" = "completed" ] || [ "$JOB_STATUS" = "failed" ]; then
        break
    fi
    
    sleep 5
done

# 4. Check final status
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/upload/status/$JOB_ID" | jq
```

## Upload Options

### Sensor Types

- `4D_NEXUS` - 4D Nexus files
- `TIFF` - TIFF image files
- `OTHER` - Other file types

### Conversion

Set `convert=true` to automatically convert files to IDX format for visualization. Set `convert=false` to store files as-is.

### Public vs Private

- `is_public=true` - Dataset is publicly accessible
- `is_public=false` - Dataset is private (default)

### Folders

Use the `folder` parameter to organize datasets:

```bash
-F "folder=CHESS_4D"
-F "folder=My_Project"
```

### Tags

Add tags for better organization:

```bash
-F "tags=nexus,4d,chess,experiment-1"
```

### Teams

Share datasets with teams:

```bash
-F "team_uuid=550e8400-e29b-41d4-a716-446655440000"
```

## Large File Uploads

For files larger than 100MB, the system automatically uses chunked uploads. You can also manually initiate chunked uploads for better control.

### Chunked Upload Example

```bash
# 1. Initiate upload
INIT_RESPONSE=$(curl -s -X POST "https://scientistcloud.com/api/upload/initiate" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_name": "Large Dataset",
       "file_size": 10737418240,
       "file_name": "large_file.nxs"
     }')

UPLOAD_ID=$(echo "$INIT_RESPONSE" | jq -r '.upload_id')
CHUNK_SIZE=$(echo "$INIT_RESPONSE" | jq -r '.chunk_size')

# 2. Upload chunks (pseudo-code)
# for each chunk in file:
#   curl -X POST "https://scientistcloud.com/api/upload/chunk" \
#        -H "Authorization: Bearer $TOKEN" \
#        -F "upload_id=$UPLOAD_ID" \
#        -F "chunk_number=$i" \
#        -F "chunk=@chunk_data"
```

## Error Handling

### File Too Large

```json
{
  "success": false,
  "error": "File too large. Maximum size: 10GB"
}
```

### Invalid File Type

```json
{
  "success": false,
  "error": "Invalid file type. Supported types: .nxs, .tiff, .tif"
}
```

### Upload Failed

```json
{
  "success": false,
  "error": "Upload failed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Best Practices

1. **Monitor Progress**: Check status regularly for large uploads
2. **Handle Errors**: Implement retry logic for failed uploads
3. **Use Chunked Uploads**: For files > 100MB, use chunked uploads
4. **Add Metadata**: Include folder, tags, and team information
5. **Verify Upload**: Check status after upload completes

## Next Steps

- See [Datasets API](?page=api-datasets) for managing uploaded datasets
- Check [Curl Scripts](?page=curl-scripts) for ready-to-use upload scripts
- Review [Python Examples](?page=python-examples) for programmatic uploads

