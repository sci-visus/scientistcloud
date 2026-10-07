# Folders

Folders are labels that group datasets in the sidebar. They do not change the on-disk path of the files. Your data, data shared with you, and team data can all use folders.

## Where Folders Appear

The account portal sidebar groups datasets under:

- **My Datasets**
- **Shared with Me**
- **Team Datasets**

Inside each group, datasets with the same folder name sit together. Datasets with no folder stay at the root of that group.

The public portal also groups public datasets by folder when a folder is set.

## Create a Folder

You can create a folder when you:

- **Upload** (Local, Google Drive, S3, or Remote): choose an existing folder or **+ Create New Folder**
- **Inspect S3 → Connect to Data Portal**: same folder selector
- **Edit** a dataset you own: change **Folder** in dataset settings

Folder is optional. Use it for experiments, instruments, or campaigns (for example `CHESS 2026`, `ReliabilityTests`, `MAGICSCAN`).

## Move a Dataset

1. Select a dataset you own
2. Click **Edit**
3. Choose another folder, create a new one, or clear the folder
4. Save

You need to be the owner. Shared and team copies follow the owner's folder assignment.

## API

Upload accepts a `folder` form field (name, not a filesystem path):

```bash
curl -X POST "https://scientistcloud.com/api/upload/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/file.nxs" \
  -F "user_email=you@example.com" \
  -F "dataset_name=Scan 42" \
  -F "sensor=4D_NEXUS" \
  -F "folder=CHESS_4D"
```

Dataset settings can also store `folder` / `folder_uuid`. See [Upload API](?page=api-upload) and [Datasets API](?page=api-datasets).
