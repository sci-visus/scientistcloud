# Python Examples for ScientistCloud

This guide provides Python examples for interacting with the ScientistCloud Data Portal API.

## Overview

Python provides a powerful way to programmatically interact with ScientistCloud. You can use the `requests` library or the provided SDK.

## Prerequisites

```bash
pip install requests
```

## Basic Authentication

### Login and Get Token

```python
import requests
import json

def login(email):
    """Login and get access token"""
    url = "https://scientistcloud.com/api/auth/login"
    response = requests.post(
        url,
        json={"email": email}
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['data']['access_token']
    else:
        print(f"Login failed: {response.text}")
        return None

# Usage
token = login("user@example.com")
print(f"Token: {token[:20]}...")
```

### Verify Token

```python
def verify_token(token):
    """Verify token is valid"""
    url = "https://scientistcloud.com/api/auth/status"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    return response.status_code == 200

# Usage
if verify_token(token):
    print("Token is valid")
```

## Upload File

### Basic Upload

```python
def upload_file(token, file_path, dataset_name, **kwargs):
    """Upload a file to ScientistCloud"""
    url = "https://scientistcloud.com/api/upload/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Prepare file
    with open(file_path, 'rb') as f:
        files = {'file': f}
        
        # Prepare form data
        data = {
            'dataset_name': dataset_name,
            'sensor': kwargs.get('sensor', '4D_NEXUS'),
            'convert': str(kwargs.get('convert', True)).lower(),
            'is_public': str(kwargs.get('is_public', False)).lower(),
        }
        
        # Add optional parameters
        if 'folder' in kwargs:
            data['folder'] = kwargs['folder']
        if 'tags' in kwargs:
            data['tags'] = kwargs['tags']
        if 'team_uuid' in kwargs:
            data['team_uuid'] = kwargs['team_uuid']
        
        # Reset file pointer
        f.seek(0)
        
        # Upload
        response = requests.post(url, headers=headers, files=files, data=data)
        
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Upload failed: {response.text}")
        return None

# Usage
result = upload_file(
    token,
    "/path/to/file.nxs",
    "My Dataset",
    sensor="4D_NEXUS",
    folder="CHESS_4D",
    tags="nexus,4d,chess"
)

if result:
    print(f"Upload started! Job ID: {result['job_id']}")
```

### Upload with Progress

```python
import os
from tqdm import tqdm

def upload_file_with_progress(token, file_path, dataset_name, **kwargs):
    """Upload file with progress bar"""
    url = "https://scientistcloud.com/api/upload/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    file_size = os.path.getsize(file_path)
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'dataset_name': dataset_name,
            'sensor': kwargs.get('sensor', '4D_NEXUS'),
            'convert': str(kwargs.get('convert', True)).lower(),
            'is_public': str(kwargs.get('is_public', False)).lower(),
        }
        
        if 'folder' in kwargs:
            data['folder'] = kwargs['folder']
        if 'tags' in kwargs:
            data['tags'] = kwargs['tags']
        
        f.seek(0)
        
        # Upload with progress
        with tqdm(total=file_size, unit='B', unit_scale=True) as pbar:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                stream=True
            )
            
            # Note: requests doesn't support progress for multipart uploads
            # This is a simplified version
            pbar.update(file_size)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Upload failed: {response.text}")
        return None
```

## Check Upload Status

```python
import time

def check_upload_status(token, job_id):
    """Check upload job status"""
    url = f"https://scientistcloud.com/api/upload/status/{job_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Status check failed: {response.text}")
        return None

def wait_for_completion(token, job_id, timeout=3600):
    """Wait for upload to complete"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = check_upload_status(token, job_id)
        
        if status:
            job_status = status.get('status')
            progress = status.get('progress_percentage', 0)
            
            print(f"Status: {job_status} ({progress}%)")
            
            if job_status == 'completed':
                print("Upload completed!")
                return status
            elif job_status == 'failed':
                print("Upload failed!")
                return status
        
        time.sleep(5)
    
    print("Timeout waiting for upload")
    return None

# Usage
job_id = result['job_id']
final_status = wait_for_completion(token, job_id)
```

## List Datasets

```python
def list_datasets(token, folder=None, team_uuid=None):
    """List user's datasets"""
    url = "https://scientistcloud.com/portal/api/datasets"
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {}
    if folder:
        params['folder'] = folder
    if team_uuid:
        params['team_uuid'] = team_uuid
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to list datasets: {response.text}")
        return None

# Usage
datasets = list_datasets(token, folder="CHESS_4D")
if datasets:
    for dataset in datasets['datasets']:
        print(f"{dataset['name']} - {dataset['status']}")
```

## Get Dataset Details

```python
def get_dataset_details(token, dataset_uuid):
    """Get dataset details"""
    url = "https://scientistcloud.com/portal/api/dataset-details"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"dataset_uuid": dataset_uuid}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get dataset details: {response.text}")
        return None

# Usage
details = get_dataset_details(token, "550e8400-e29b-41d4-a716-446655440000")
if details:
    print(f"Dataset: {details['dataset']['name']}")
    print(f"Status: {details['dataset']['status']}")
```

## Update Dataset

```python
def update_dataset(token, dataset_uuid, **kwargs):
    """Update dataset metadata"""
    url = "https://scientistcloud.com/portal/api/update-dataset"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {"dataset_uuid": dataset_uuid}
    
    # Add update fields
    if 'name' in kwargs:
        data['name'] = kwargs['name']
    if 'tags' in kwargs:
        data['tags'] = kwargs['tags']
    if 'folder' in kwargs:
        data['folder'] = kwargs['folder']
    if 'team_uuid' in kwargs:
        data['team_uuid'] = kwargs['team_uuid']
    if 'dimensions' in kwargs:
        data['dimensions'] = kwargs['dimensions']
    if 'preferred_dashboard' in kwargs:
        data['preferred_dashboard'] = kwargs['preferred_dashboard']
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Update failed: {response.text}")
        return None

# Usage
result = update_dataset(
    token,
    "550e8400-e29b-41d4-a716-446655440000",
    name="Updated Name",
    tags="updated, tags"
)
```

## Complete Example

```python
#!/usr/bin/env python3
"""Complete example: Upload file and monitor progress"""

import requests
import time
import sys

# Configuration
EMAIL = "user@example.com"
FILE_PATH = "/path/to/file.nxs"
DATASET_NAME = "My Dataset"
FOLDER = "CHESS_4D"

# 1. Login
print("Logging in...")
login_response = requests.post(
    "https://scientistcloud.com/api/auth/login",
    json={"email": EMAIL}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    sys.exit(1)

token = login_response.json()['data']['access_token']
print(f"✅ Token obtained: {token[:20]}...")

# 2. Upload file
print(f"\nUploading {FILE_PATH}...")
with open(FILE_PATH, 'rb') as f:
    files = {'file': f}
    data = {
        'dataset_name': DATASET_NAME,
        'sensor': '4D_NEXUS',
        'convert': 'true',
        'is_public': 'false',
        'folder': FOLDER,
        'tags': 'nexus,4d'
    }
    
    f.seek(0)
    upload_response = requests.post(
        "https://scientistcloud.com/api/upload/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data
    )

if upload_response.status_code != 200:
    print(f"Upload failed: {upload_response.text}")
    sys.exit(1)

result = upload_response.json()
job_id = result['job_id']
dataset_uuid = result['dataset_uuid']

print(f"✅ Upload started! Job ID: {job_id}")
print(f"📊 Dataset UUID: {dataset_uuid}")

# 3. Monitor progress
print("\n📊 Monitoring upload progress...")
while True:
    status_response = requests.get(
        f"https://scientistcloud.com/api/upload/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if status_response.status_code == 200:
        status = status_response.json()
        job_status = status.get('status')
        progress = status.get('progress_percentage', 0)
        
        print(f"Status: {job_status} ({progress}%)")
        
        if job_status == 'completed':
            print("✅ Upload completed!")
            break
        elif job_status == 'failed':
            print("❌ Upload failed!")
            sys.exit(1)
    
    time.sleep(5)

# 4. Get dataset details
print("\n📋 Getting dataset details...")
details_response = requests.get(
    "https://scientistcloud.com/portal/api/dataset-details",
    headers={"Authorization": f"Bearer {token}"},
    params={"dataset_uuid": dataset_uuid}
)

if details_response.status_code == 200:
    details = details_response.json()
    print(f"Dataset: {details['dataset']['name']}")
    print(f"Status: {details['dataset']['status']}")
    print(f"Created: {details['dataset']['created_at']}")

print("\n✅ Done!")
```

## Using the SDK

If you have access to the ScientistCloud SDK:

```python
from scientistcloud import ScientistCloudClient

# Initialize client
client = ScientistCloudClient(
    auth_url="https://scientistcloud.com",
    api_url="https://scientistcloud.com"
)

# Login
client.login("user@example.com")

# Upload file
result = client.upload_file(
    file_path="/path/to/file.nxs",
    dataset_name="My Dataset",
    sensor="4D_NEXUS",
    folder="CHESS_4D"
)

# Check status
status = client.get_upload_status(result['job_id'])

# List datasets
datasets = client.list_datasets(folder="CHESS_4D")
```

## Error Handling

```python
def safe_upload(token, file_path, dataset_name):
    """Upload with error handling"""
    try:
        result = upload_file(token, file_path, dataset_name)
        
        if result and 'job_id' in result:
            return result
        else:
            print("Upload failed: No job_id in response")
            return None
            
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

## Best Practices

1. **Handle Errors**: Always check response status codes
2. **Use Context Managers**: Use `with` statements for file operations
3. **Token Management**: Store tokens securely, refresh when expired
4. **Progress Monitoring**: Monitor upload progress for large files
5. **Retry Logic**: Implement retry logic for network errors

## Next Steps

- See [API Documentation](?page=api) for complete API reference
- Check [Curl Scripts](?page=curl-scripts) for command-line alternatives
- Review [Getting Started](?page=getting-started) for setup instructions

