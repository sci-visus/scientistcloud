# Curl Scripts for ScientistCloud

This guide explains how to use and customize curl-based scripts for uploading files and managing datasets in ScientistCloud.

## Overview

Curl scripts provide a convenient way to automate uploads and dataset management from the command line. They handle authentication, file uploads, and status monitoring.

## Quick Upload Script

The quick upload script (`curl_for_chess.sh`) is a generalized script that can be customized for your use case.

### Basic Usage

```bash
# Use command-line parameters
./curl_for_chess.sh -u amy@visus.net -f /fullpath/file.nxs -n "Dataset Name"

# Use defaults (no parameters needed)
./curl_for_chess.sh

# Mix and match (some defaults, some parameters)
./curl_for_chess.sh -f /new/path/file.nxs -n "New Dataset Name"

# Show help
./curl_for_chess.sh -h
```

## Script Template

Here's a generalized template you can customize:

```bash
#!/bin/bash
# Quick Upload Script for ScientistCloud
# 
# Usage:
#   ./upload_script.sh -u email@example.com -f /path/to/file.nxs -n "Dataset Name"
#   ./upload_script.sh  # Uses defaults set below
#
# Options:
#   -u  User email (required if not set as default)
#   -f  File path (required if not set as default)
#   -n  Dataset name (required if not set as default)
#   -F  Folder name (optional, defaults to MY_FOLDER)
#   -t  Team UUID (optional, defaults to MY_TEAM)
#   -h  Show this help message

# ============================================
# DEFAULT VALUES (edit these or use -u/-f/-n flags)
# ============================================
DEFAULT_USER_EMAIL="your@email.com"
DEFAULT_FILE_PATH="/path/to/default/file.nxs"
DEFAULT_DATASET_NAME="Default Dataset Name"
DEFAULT_FOLDER="MY_FOLDER"
DEFAULT_TEAM_UUID="MY_TEAM"

# ============================================
# PARSE COMMAND LINE ARGUMENTS
# ============================================
USER_EMAIL=""
FILE_PATH=""
DATASET_NAME=""
FOLDER="$DEFAULT_FOLDER"
TEAM_UUID="$DEFAULT_TEAM_UUID"

show_help() {
    cat << EOF
Quick Upload Script for ScientistCloud

Usage:
    $0 [OPTIONS]

Options:
    -u EMAIL         User email (required if not set as default)
    -f FILE_PATH     Full path to file (required if not set as default)
    -n DATASET_NAME  Dataset name (required if not set as default)
    -F FOLDER        Folder name (optional, default: $DEFAULT_FOLDER)
    -t TEAM_UUID     Team UUID (optional, default: $DEFAULT_TEAM_UUID)
    -h               Show this help message

Examples:
    $0 -u user@example.com -f /path/to/file.nxs -n "My Dataset"
    $0  # Uses defaults set in script

Defaults (edit script to change):
    Email: $DEFAULT_USER_EMAIL
    File:  $DEFAULT_FILE_PATH
    Name:  $DEFAULT_DATASET_NAME
EOF
    exit 0
}

while getopts "u:f:n:F:t:h" opt; do
    case $opt in
        u)
            USER_EMAIL="$OPTARG"
            ;;
        f)
            FILE_PATH="$OPTARG"
            ;;
        n)
            DATASET_NAME="$OPTARG"
            ;;
        F)
            FOLDER="$OPTARG"
            ;;
        t)
            TEAM_UUID="$OPTARG"
            ;;
        h)
            show_help
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            echo "Use -h for help"
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

# Use defaults if not provided via command line
USER_EMAIL="${USER_EMAIL:-$DEFAULT_USER_EMAIL}"
FILE_PATH="${FILE_PATH:-$DEFAULT_FILE_PATH}"
DATASET_NAME="${DATASET_NAME:-$DEFAULT_DATASET_NAME}"

# Validate required parameters
if [ -z "$USER_EMAIL" ]; then
    echo "❌ Error: User email is required. Use -u flag or set DEFAULT_USER_EMAIL in script."
    exit 1
fi

if [ -z "$FILE_PATH" ]; then
    echo "❌ Error: File path is required. Use -f flag or set DEFAULT_FILE_PATH in script."
    exit 1
fi

if [ -z "$DATASET_NAME" ]; then
    echo "❌ Error: Dataset name is required. Use -n flag or set DEFAULT_DATASET_NAME in script."
    exit 1
fi

# ============================================
# AUTHENTICATION
# ============================================
echo "🔐 Authenticating..."
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"$USER_EMAIL\"}" | \
     jq -r '.data.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Failed to get token. Check your email and try again."
    exit 1
fi
echo "✅ Token obtained: ${TOKEN:0:20}..."

# Verify token works
echo "🔍 Verifying token..."
curl -s "https://scientistcloud.com/api/auth/status" \
     -H "Authorization: Bearer $TOKEN" | jq -r '.message // .error // "Token verified"'

# ============================================
# FILE VALIDATION
# ============================================
if [ ! -f "$FILE_PATH" ]; then
    echo "❌ Error: File not found: $FILE_PATH"
    echo "💡 Tip: Use absolute path and check for typos"
    exit 1
fi

echo "📁 Uploading: $(basename "$FILE_PATH") ($(du -h "$FILE_PATH" | cut -f1))"

# ============================================
# UPLOAD
# ============================================
echo "🚀 Starting upload (this may take a while for large files)..."
echo ""

# Upload with progress bar
curl --progress-bar --write-out "\nHTTP_CODE:%{http_code}\n" \
     -o /tmp/upload_response.json \
     -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@$FILE_PATH" \
     -F "user_email=$USER_EMAIL" \
     -F "dataset_name=$DATASET_NAME" \
     -F "sensor=4D_NEXUS" \
     -F "convert=false" \
     -F "is_public=true" \
     -F "folder=$FOLDER" \
     -F "tags=nexus,4d" 2>&1 | tee /tmp/upload_output.txt

HTTP_CODE=$(grep "HTTP_CODE:" /tmp/upload_output.txt | tail -1 | cut -d: -f2)
RESPONSE=$(cat /tmp/upload_response.json)
echo ""

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id // empty')
    if [ "$JOB_ID" != "null" ] && [ -n "$JOB_ID" ]; then
        echo "✅ Upload started! Job ID: $JOB_ID"
        echo "📊 Response:"
        echo "$RESPONSE" | jq
    else
        echo "❌ Upload failed - no job_id in response"
        echo "📊 Response:"
        echo "$RESPONSE" | jq 2>/dev/null || echo "$RESPONSE"
    fi
else
    echo "❌ Upload failed with HTTP $HTTP_CODE"
    echo "📊 Response:"
    echo "$RESPONSE" | jq 2>/dev/null || echo "$RESPONSE"
    JOB_ID=""
fi

# ============================================
# CHECK UPLOAD STATUS (Optional)
# ============================================
if [ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ]; then
    echo ""
    echo "📊 Checking upload status..."
    curl -s "https://scientistcloud.com/api/upload/status/$JOB_ID" \
         -H "Authorization: Bearer $TOKEN" | jq
else
    echo ""
    echo "ℹ️  Skipping status check (upload did not succeed)"
fi
```

## Customization Guide

### Step 1: Set Your Defaults

Edit the default values at the top of the script:

```bash
DEFAULT_USER_EMAIL="your@email.com"
DEFAULT_FILE_PATH="/path/to/your/default/file.nxs"
DEFAULT_DATASET_NAME="Your Default Dataset Name"
DEFAULT_FOLDER="YOUR_FOLDER"
DEFAULT_TEAM_UUID="YOUR_TEAM_UUID"
```

### Step 2: Customize Upload Parameters

Modify the upload section to match your needs:

```bash
# Change sensor type
-F "sensor=TIFF"  # or "OTHER"

# Change conversion setting
-F "convert=true"  # Convert to IDX format

# Change visibility
-F "is_public=false"  # Make private

# Add custom tags
-F "tags=your,tags,here"
```

### Step 3: Add Team Support

If you want to use team UUIDs:

```bash
# Add team UUID to upload
if [ -n "$TEAM_UUID" ] && [ "$TEAM_UUID" != "MY_TEAM" ]; then
    -F "team_uuid=$TEAM_UUID"
fi
```

## Advanced Features

### Monitor Upload Progress

Add a loop to monitor upload progress:

```bash
if [ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ]; then
    echo "📊 Monitoring upload progress..."
    while true; do
        STATUS=$(curl -s "https://scientistcloud.com/api/upload/status/$JOB_ID" \
             -H "Authorization: Bearer $TOKEN")
        
        PROGRESS=$(echo "$STATUS" | jq -r '.progress_percentage')
        JOB_STATUS=$(echo "$STATUS" | jq -r '.status')
        
        echo "Status: $JOB_STATUS ($PROGRESS%)"
        
        if [ "$JOB_STATUS" = "completed" ] || [ "$JOB_STATUS" = "failed" ]; then
            break
        fi
        
        sleep 5
    done
fi
```

### Batch Upload

Create a script to upload multiple files:

```bash
#!/bin/bash
# Batch upload script

FILES=(
    "/path/to/file1.nxs"
    "/path/to/file2.nxs"
    "/path/to/file3.nxs"
)

USER_EMAIL="your@email.com"
FOLDER="BATCH_UPLOAD"

# Authenticate once
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"$USER_EMAIL\"}" | \
     jq -r '.data.access_token')

# Upload each file
for FILE in "${FILES[@]}"; do
    DATASET_NAME=$(basename "$FILE")
    echo "Uploading $DATASET_NAME..."
    
    curl -X POST "https://scientistcloud.com/api/upload/upload" \
         -H "Authorization: Bearer $TOKEN" \
         -F "file=@$FILE" \
         -F "dataset_name=$DATASET_NAME" \
         -F "folder=$FOLDER" \
         -F "sensor=4D_NEXUS"
    
    echo ""
done
```

### List Datasets

Add a function to list datasets:

```bash
list_datasets() {
    curl -s "https://scientistcloud.com/portal/api/datasets" \
         -H "Authorization: Bearer $TOKEN" | jq '.datasets[] | {uuid, name, status}'
}
```

## Common Use Cases

### Upload to Specific Folder

```bash
./upload_script.sh -f /path/to/file.nxs -n "Dataset" -F "CHESS_4D"
```

### Upload with Tags

Modify the script to accept tags:

```bash
# Add -T option for tags
-T)
    TAGS="$OPTARG"
    ;;
    
# Use in upload
-F "tags=$TAGS"
```

### Upload to Team

```bash
./upload_script.sh -f /path/to/file.nxs -n "Dataset" -t "team-uuid-here"
```

## Troubleshooting

### Authentication Failed

```bash
# Check if email is correct
curl -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}'
```

### File Not Found

```bash
# Use absolute paths
FILE_PATH="/absolute/path/to/file.nxs"

# Check file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "File not found: $FILE_PATH"
    exit 1
fi
```

### Upload Failed

```bash
# Check HTTP response code
echo "HTTP Code: $HTTP_CODE"

# Check response message
echo "$RESPONSE" | jq '.error // .message'
```

## Best Practices

1. **Use Absolute Paths**: Always use full file paths
2. **Set Defaults**: Configure default values for your workflow
3. **Handle Errors**: Check for errors and exit appropriately
4. **Monitor Progress**: Add status checking for large uploads
5. **Secure Tokens**: Don't hardcode tokens in scripts

## Example Scripts

### Minimal Upload Script

```bash
#!/bin/bash
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"$1\"}" | jq -r '.data.access_token')

curl -X POST "https://scientistcloud.com/api/upload/upload" \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@$2" \
     -F "dataset_name=$3"
```

Usage: `./minimal.sh email@example.com /path/to/file.nxs "Dataset Name"`

## Next Steps

- See [Upload API](?page=api-upload) for detailed API documentation
- Check [Python Examples](?page=python-examples) for programmatic access
- Review [Getting Started](?page=getting-started) for setup instructions

