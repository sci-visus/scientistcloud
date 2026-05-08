# Datasets API

Current dataset APIs are under `/api/v1/datasets`.

## Identifier Rules

Most dataset routes accept `{identifier}` as:

- UUID
- slug
- numeric ID
- dataset name

## Core Endpoints

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/v1/datasets` | GET | List datasets |
| `/api/v1/datasets/by-user` | GET | Grouped view (`my`, `shared`, `team`) |
| `/api/v1/datasets/public` | GET | Public datasets |
| `/api/v1/datasets/public/{identifier}` | GET | Public dataset details |
| `/api/v1/datasets` | POST | Create dataset metadata |
| `/api/v1/datasets/{identifier}` | GET | Get dataset |
| `/api/v1/datasets/{identifier}` | PUT | Update dataset |
| `/api/v1/datasets/{identifier}` | DELETE | Delete dataset |
| `/api/v1/datasets/{identifier}/status` | GET | Dataset status |
| `/api/v1/datasets/{identifier}/convert` | POST | Trigger conversion |

## List / Query

### GET `/api/v1/datasets`

Supports optional filters including `name`, `slug`, `id`, `user_email`, and `team_uuid`.

```bash
curl -s "https://scientistcloud.com/api/v1/datasets?user_email=user@example.com" | jq
```

### GET `/api/v1/datasets/by-user`

```bash
curl -s "https://scientistcloud.com/api/v1/datasets/by-user?user_email=user@example.com" | jq
```

Response includes:

- `datasets.my`
- `datasets.shared`
- `datasets.team`
- `counts`

## Dataset CRUD

### POST `/api/v1/datasets`

```bash
curl -s -X POST "https://scientistcloud.com/api/v1/datasets?user_email=user@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Example Dataset",
    "sensor":"4D_NEXUS",
    "description":"created via API",
    "tags":"nexus,example",
    "is_public":false,
    "is_downloadable":"only owner"
  }' | jq
```

### GET `/api/v1/datasets/{identifier}`

```bash
curl -s "https://scientistcloud.com/api/v1/datasets/example-dataset?user_email=user@example.com" | jq
```

### PUT `/api/v1/datasets/{identifier}`

`user_email` is required for updates.

```bash
curl -s -X PUT "https://scientistcloud.com/api/v1/datasets/example-dataset?user_email=user@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "description":"updated",
    "tags":"nexus,updated",
    "is_public":false
  }' | jq
```

### DELETE `/api/v1/datasets/{identifier}`

`user_email` is required and must be owner.

```bash
curl -s -X DELETE "https://scientistcloud.com/api/v1/datasets/example-dataset?user_email=user@example.com" | jq
```

## Dataset Status + Conversion

```bash
curl -s "https://scientistcloud.com/api/v1/datasets/example-dataset/status?user_email=user@example.com" | jq
curl -s -X POST "https://scientistcloud.com/api/v1/datasets/example-dataset/convert?user_email=user@example.com" | jq
```

## File Operations

| Endpoint | Method |
|----------|--------|
| `/api/v1/datasets/{identifier}/files` | POST |
| `/api/v1/datasets/{identifier}/files` | GET |
| `/api/v1/datasets/{identifier}/files/{file_id}` | DELETE |
| `/api/v1/datasets/{identifier}/file-content` | GET |
| `/api/v1/datasets/{identifier}/file-serve` | GET |
| `/api/v1/datasets/{identifier}/settings` | GET/PUT |
| `/api/v1/datasets/{identifier}/size` | GET |

## New S3 Helpers

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/v1/datasets/s3/presign` | POST | Signed/public URL generation for S3-backed data |
| `/api/v1/datasets/s3/openvisus-resolved-idx` | POST | Build resolved idx for OpenVisus |

Both S3 helpers accept `dataset_identifier` or direct `s3_uri` and support runtime S3 credentials.

