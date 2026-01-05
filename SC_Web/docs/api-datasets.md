# Datasets API

The Datasets API allows you to manage datasets, including listing, viewing details, updating metadata, and deleting datasets.

## List Datasets

### GET `/portal/api/datasets`

Get all datasets accessible to the authenticated user.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets"
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder` | String | Filter by folder name |
| `team_uuid` | String | Filter by team UUID |
| `status` | String | Filter by status |
| `page` | Integer | Page number (pagination) |
| `limit` | Integer | Results per page |

**Response:**

```json
{
  "success": true,
  "datasets": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Dataset",
      "sensor": "4D_NEXUS",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "folder": "CHESS_4D",
      "tags": ["nexus", "4d", "chess"]
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 50
}
```

## Get Dataset Details

### GET `/portal/api/dataset-details`

Get detailed information about a specific dataset.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-details?dataset_uuid=550e8400-e29b-41d4-a716-446655440000"
```

**Query Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `dataset_uuid` | Yes | Dataset UUID |

**Response:**

```json
{
  "success": true,
  "dataset": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Dataset",
    "sensor": "4D_NEXUS",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "folder": "CHESS_4D",
    "team_uuid": "team-uuid-here",
    "tags": ["nexus", "4d", "chess"],
    "dimensions": "1024x1024x100",
    "preferred_dashboard": "4D_Dashboard",
    "is_public": false,
    "file_count": 5,
    "total_size": 1073741824
  }
}
```

## List Dataset Files

### GET `/portal/api/dataset-files`

Get the file structure for a dataset.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-files?dataset_uuid=550e8400-e29b-41d4-a716-446655440000"
```

**Query Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `dataset_uuid` | Yes | Dataset UUID |
| `directory` | No | Filter by directory: `upload` or `converted` |

**Response:**

```json
{
  "success": true,
  "files": [
    {
      "name": "file.nxs",
      "path": "file.nxs",
      "size": 1073741824,
      "type": "file",
      "directory": "upload"
    },
    {
      "name": "file.idx",
      "path": "file.idx",
      "size": 2147483648,
      "type": "file",
      "directory": "converted"
    }
  ],
  "directories": {
    "upload": {
      "file_count": 1,
      "total_size": 1073741824
    },
    "converted": {
      "file_count": 1,
      "total_size": 2147483648
    }
  }
}
```

## Update Dataset

### POST `/portal/api/update-dataset`

Update dataset metadata.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/portal/api/update-dataset" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
       "name": "Updated Dataset Name",
       "tags": "tag1, tag2, tag3",
       "folder": "New_Folder",
       "team_uuid": "team-uuid-here",
       "dimensions": "1024x1024x100",
       "preferred_dashboard": "4D_Dashboard"
     }'
```

**Request Body:**

| Field | Type | Description |
|-------|------|-------------|
| `dataset_uuid` | String | Dataset UUID (required) |
| `name` | String | New dataset name |
| `tags` | String | Comma-separated tags |
| `folder` | String | Folder name |
| `team_uuid` | String | Team UUID |
| `dimensions` | String | Dataset dimensions |
| `preferred_dashboard` | String | Preferred dashboard type |

**Response:**

```json
{
  "success": true,
  "message": "Dataset updated successfully",
  "dataset": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Updated Dataset Name",
    "tags": ["tag1", "tag2", "tag3"]
  }
}
```

## Delete Dataset

### POST `/portal/api/delete-dataset`

Delete a dataset.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/portal/api/delete-dataset" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000"
     }'
```

**Response:**

```json
{
  "success": true,
  "message": "Dataset deleted successfully"
}
```

## Get Dataset Status

### GET `/portal/api/dataset-status`

Get the processing status of a dataset.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-status?dataset_uuid=550e8400-e29b-41d4-a716-446655440000"
```

**Response:**

```json
{
  "success": true,
  "status": "completed",
  "progress_percentage": 100,
  "message": "Dataset processing complete"
}
```

## Get Dataset File Content

### GET `/portal/api/dataset-file-content`

Get the content of a specific file in a dataset.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-file-content?dataset_uuid=550e8400-e29b-41d4-a716-446655440000&file_path=file.nxs&directory=upload"
```

**Query Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `dataset_uuid` | Yes | Dataset UUID |
| `file_path` | Yes | Path to file within dataset |
| `directory` | Yes | Directory: `upload` or `converted` |

## Complete Example

```bash
#!/bin/bash

# Authenticate
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')

# 1. List all datasets
echo "Listing datasets..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets" | jq

# 2. Get dataset details
DATASET_UUID="550e8400-e29b-41d4-a716-446655440000"
echo "Getting dataset details..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-details?dataset_uuid=$DATASET_UUID" | jq

# 3. List dataset files
echo "Listing dataset files..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-files?dataset_uuid=$DATASET_UUID" | jq

# 4. Update dataset
echo "Updating dataset..."
curl -s -X POST "https://scientistcloud.com/portal/api/update-dataset" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{
       \"dataset_uuid\": \"$DATASET_UUID\",
       \"name\": \"Updated Name\",
       \"tags\": \"updated, tags\"
     }" | jq

# 5. Check status
echo "Checking dataset status..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/dataset-status?dataset_uuid=$DATASET_UUID" | jq
```

## Filtering and Sorting

### Filter by Folder

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets?folder=CHESS_4D"
```

### Filter by Team

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets?team_uuid=team-uuid-here"
```

### Filter by Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets?status=completed"
```

### Pagination

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets?page=1&limit=20"
```

## Dashboard Types

The `preferred_dashboard` field can be set to:

- `4D_Dashboard` - 4D visualization dashboard
- `OpenVisusSlice` - OpenVisus slice viewer
- `3DVTK` - 3D VTK viewer
- `Other` - Other dashboard types

## Error Handling

### Dataset Not Found

```json
{
  "success": false,
  "error": "Dataset not found",
  "code": "DATASET_NOT_FOUND"
}
```

### Access Denied

```json
{
  "success": false,
  "error": "Access denied",
  "code": "ACCESS_DENIED"
}
```

## Best Practices

1. **Use UUIDs**: Always use dataset UUIDs for reliable identification
2. **Check Status**: Verify dataset status before operations
3. **Handle Errors**: Implement proper error handling
4. **Update Metadata**: Keep dataset metadata up-to-date
5. **Organize with Folders**: Use folders to organize datasets

## Next Steps

- See [Upload API](?page=api-upload) for uploading datasets
- Check [Curl Scripts](?page=curl-scripts) for automation examples
- Review [Python Examples](?page=python-examples) for programmatic access

