# Upload File Paths Documentation

## Overview

This document explains where uploaded files are stored in the ScientistCloud system.

## File Storage Structure

When a user uploads data, files are organized by dataset UUID in two main directories:

### 1. Upload Directory (Original Files)
- **Path**: `{JOB_IN_DATA_DIR}/{dataset_uuid}/`
- **Default**: `/mnt/visus_datasets/upload/{dataset_uuid}/`
- **Purpose**: Stores the original uploaded files before conversion
- **Example**: `/mnt/visus_datasets/upload/550e8400-e29b-41d4-a716-446655440000/`

### 2. Converted Directory (Processed Files)
- **Path**: `{JOB_OUT_DATA_DIR}/{dataset_uuid}/`
- **Default**: `/mnt/visus_datasets/converted/{dataset_uuid}/`
- **Purpose**: Stores converted/processed files (e.g., IDX files)
- **Example**: `/mnt/visus_datasets/converted/550e8400-e29b-41d4-a716-446655440000/`

## Configuration

### Environment Variables

The paths are controlled by environment variables:

- `JOB_IN_DATA_DIR`: Directory for uploaded files (default: `/mnt/visus_datasets/upload`)
- `JOB_OUT_DATA_DIR`: Directory for converted files (default: `/mnt/visus_datasets/converted`)
- `VISUS_DATASETS`: Base directory for all datasets (used for volume mounting)

### Docker Configuration

In Docker, the paths are configured as follows:

**docker-compose.yml** (FastAPI service):
```yaml
environment:
  JOB_IN_DATA_DIR: /mnt/visus_datasets/upload
  JOB_OUT_DATA_DIR: /mnt/visus_datasets/converted
volumes:
  - ${VISUS_DATASETS}:/mnt/visus_datasets
```

**Note**: The `${VISUS_DATASETS}` environment variable on the host is mounted to `/mnt/visus_datasets` inside the container.

### Path Configuration

The paths are configured in the Dockerfile and docker-compose.yml:

**Dockerfile.fastapi** creates the base directory structure:
```dockerfile
RUN mkdir -p /mnt/visus_datasets/upload /mnt/visus_datasets/converted ...
```

**docker-compose.yml** sets the environment variables:
- `JOB_IN_DATA_DIR: /mnt/visus_datasets/upload`
- `JOB_OUT_DATA_DIR: /mnt/visus_datasets/converted`

The actual paths used are:
- `/mnt/visus_datasets/upload/{uuid}` (from `JOB_IN_DATA_DIR`)
- `/mnt/visus_datasets/converted/{uuid}` (from `JOB_OUT_DATA_DIR`)

## Code Reference

### Upload Job Creation
**File**: `SCLib_JobProcessing/SCLib_UploadJobTypes.py` (line 309)
```python
base_path = f"{os.getenv('JOB_IN_DATA_DIR', '/mnt/visus_datasets/upload')}/{dataset_uuid}"
```

### File Processing
**File**: `SCLib_JobProcessing/SCLib_UploadProcessor.py` (line 161)
```python
dest_dir = Path(job_config.destination_path)
dest_dir.mkdir(parents=True, exist_ok=True)
```

The `destination_path` is constructed from `JOB_IN_DATA_DIR` + `dataset_uuid`.

## File Browser API

The file browser (`api/dataset-files.php`) reads from:
- `JOB_IN_DATA_DIR/{uuid}` → Shows as "Upload" folder
- `JOB_OUT_DATA_DIR/{uuid}` → Shows as "Converted" folder

## Troubleshooting

### Verify File Locations

1. **Check environment variables**:
   ```bash
   docker exec sclib_fastapi env | grep JOB_IN_DATA_DIR
   ```
   Should show: `JOB_IN_DATA_DIR=/mnt/visus_datasets/upload`

2. **Verify volume mount**:
   ```bash
   docker exec sclib_fastapi ls -la /mnt/visus_datasets
   ```

3. **Check actual file locations**:
   ```bash
   docker exec sclib_fastapi ls -la /mnt/visus_datasets/upload
   docker exec sclib_fastapi ls -la /mnt/visus_datasets/converted
   ```

### Expected Behavior

Files are stored at:
- **Upload**: `/mnt/visus_datasets/upload/{dataset_uuid}/`
- **Converted**: `/mnt/visus_datasets/converted/{dataset_uuid}/`

These paths are controlled by the `JOB_IN_DATA_DIR` and `JOB_OUT_DATA_DIR` environment variables set in docker-compose.yml.

