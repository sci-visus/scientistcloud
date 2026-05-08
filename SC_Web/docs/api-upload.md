# Upload API

The upload service manages file ingestion and job tracking.

## Main Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload/upload` | POST | Upload file contents |
| `/api/upload/upload-path` | POST | Upload using a server-visible file path |
| `/api/upload/status/{job_id}` | GET | Check one upload job |
| `/api/upload/jobs` | GET | List upload jobs |
| `/api/upload/cancel/{job_id}` | POST | Cancel a job |
| `/api/upload/supported-sources` | GET | Supported source/sensor enums |
| `/api/upload/limits` | GET | Size/threshold limits |
| `/api/upload/initiate` | POST | Source-based upload initiation API |

## POST `/api/upload/upload`

### Required form fields

- `file`
- `user_email`
- `dataset_name`
- `sensor`

### Common optional fields

- `convert` (`true|false`, default `false`)
- `is_public` (`true|false`, default `false`)
- `is_downloadable` (`only owner`, `only team`, `public`)
- `folder`
- `relative_path` (directory uploads)
- `team_uuid`
- `tags` (comma-separated)
- `dataset_identifier` (uuid/slug/id/name)
- `add_to_existing` (`true|false`)
- `expected_files` (JSON manifest)

### Example

```bash
curl -s -X POST "https://scientistcloud.com/api/upload/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/file.nxs" \
  -F "user_email=user@example.com" \
  -F "dataset_name=My Dataset" \
  -F "sensor=4D_NEXUS" \
  -F "convert=false" \
  -F "is_public=false" \
  -F "is_downloadable=only owner" \
  -F "folder=CHESS_4D" \
  -F "tags=nexus,4d,chess"
```

### Response shape

```json
{
  "job_id": "job_...",
  "status": "queued",
  "message": "Upload job initiated ...",
  "estimated_duration": 300,
  "upload_type": "standard",
  "dataset_uuid": "uuid..."
}
```

## POST `/api/upload/upload-path`

Use when the file path is already accessible on the server runtime (for example mounted volumes).

```bash
curl -s -X POST "https://scientistcloud.com/api/upload/upload-path" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_path=/mnt/visus_datasets/input/file.nxs" \
  -F "user_email=user@example.com" \
  -F "dataset_name=Path Upload Dataset" \
  -F "sensor=4D_NEXUS" \
  -F "convert=false"
```

## GET `/api/upload/status/{job_id}`

```bash
curl -s "https://scientistcloud.com/api/upload/status/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Typical fields include `status`, `canonical_state`, `progress_percentage`, `bytes_uploaded`, `bytes_total`, `message`, and `error`.

## GET `/api/upload/jobs`

```bash
curl -s "https://scientistcloud.com/api/upload/jobs?user_id=user@example.com" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## POST `/api/upload/cancel/{job_id}`

```bash
curl -s -X POST "https://scientistcloud.com/api/upload/cancel/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Utility Endpoints

```bash
curl -s "https://scientistcloud.com/api/upload/supported-sources" | jq
curl -s "https://scientistcloud.com/api/upload/limits" | jq
```

## Notes

- Files larger than the configured threshold are handled with chunked logic automatically by the unified upload API.
- Use `relative_path` + shared `dataset_identifier` when uploading a directory tree file-by-file.
- `folder` is UI metadata, not on-disk path structure.

