# Inspect S3

Inspect S3 lets you browse an S3-compatible bucket (AWS, Wasabi, MinIO, and similar), preview files, and register a dataset in the portal without a local upload.

This tool is on the **account portal** only (`Inspect S3` in the toolbar). The public portal cannot connect to your bucket.

## Connect

1. Sign in at `https://scientistcloud.com/portal/index.php`
2. Click **Inspect S3**
3. Enter endpoint, bucket, prefix, region, and credentials
4. Use **path-style addressing** for Wasabi, MinIO, and many S3-compatible gateways
5. Connect, then browse folders and files

You can also start from **Upload → S3** and paste an `s3://` or HTTPS object URL.

## Browse and Preview

- Open prefixes like a file tree
- **Preview** text-like files (`.idx`, `.txt`, `.csv`, `.json`, `.md`)
- **Download** a file or **Download Folder** as a zip
- **Copy S3/HTTP Link** for the Upload S3 form
- **Copy Link** creates a time-limited signed download URL

## Link a Dataset to the Portal

For an existing `.idx` (and similar ready-to-stream data):

1. Click **Connect to Data Portal**
2. Fill **Create Remote Dataset**: name, sensor (often `IDX`), folder, team, preferred dashboard
3. **Download from S3 to server**: copies objects under the portal upload directory
4. **Queue conversion**: leave off if the data is already IDX / ready to view
5. Click **Show in Data Portal**

Typical combinations:

- Already IDX: Download on, Convert off
- Link only (stream from the bucket): both unchecked
- Raw data that needs conversion: Download on, Convert on

The new dataset appears in your sidebar, in the folder you chose, and opens in a [dashboard](?page=dashboards).

## Upload tab (S3)

From **Upload**, the **S3** tab accepts:

- A single S3/HTTP link, or
- Explicit endpoint / bucket / prefix / keys

You can test the connection, choose a folder and team, and optionally convert.

## Related

- [Folders](?page=folders)
- [Upload API](?page=api-upload) (S3 source / link)
- [Datasets API](?page=api-datasets) S3 helpers (`/api/v1/datasets/s3/presign`, `/api/v1/datasets/s3/openvisus-resolved-idx`)
