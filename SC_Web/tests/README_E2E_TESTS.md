# End-to-End Upload Test Suite for SC_Web

This test suite tests the **complete upload flow** through SC_Web's PHP proxy layer, catching bugs that occur in:

- **PHP proxy layer** (`upload-dataset.php`, `upload-status.php`)
- **Authentication handling**
- **Error handling and response parsing**
- **Status polling**
- **Full user workflow**

## Why This Test Suite?

The previous test suite (`test_upload_automated.py` in SCLib) tests the FastAPI service **directly**, but SC_Web uses a **PHP proxy layer** that:

1. Handles authentication
2. Forwards requests to FastAPI
3. Parses and returns responses
4. Handles errors

**Bugs often occur in this PHP layer**, which is why you're finding issues when building. This test suite tests the **actual flow** that users experience.

## Architecture

```
Frontend (JS) → PHP Proxy → FastAPI Upload API
                ↓
            Error Handling
            Response Parsing
            Authentication
```

This test suite simulates the frontend by calling the PHP endpoints directly.

## Quick Start

### Prerequisites

1. **SC_Web Running**: The SC_Web application should be running
   ```bash
   # Default URL: http://localhost
   # Can be configured via SC_WEB_BASE_URL environment variable
   ```

2. **Python Dependencies**:
   ```bash
   pip install pytest requests
   ```

3. **Test Files**: Update paths in `test_upload_config.py`

### Running Tests

```bash
cd scientistcloud/SC_Web/tests
pytest test_upload_e2e.py -v
pytest test_upload_e2e.py::TestSCWebLocalUploads -v
pytest test_upload_e2e.py::TestSCWebErrorHandling -v
```

## What Gets Tested

### 1. Local File Uploads
- 4D Nexus files through SC_Web
- TIFF RGB files through SC_Web
- IDX files through SC_Web

### 2. Error Handling
- Missing file errors
- Invalid sensor types
- Authentication errors
- Response parsing errors

### 3. Status Polling
- Status endpoint through PHP proxy
- Status transitions
- Completion verification

## Configuration

Edit `test_upload_config.py`:

```python
class TestConfig:
    # SC_Web settings
    SC_WEB_BASE_URL = "http://localhost"
    SC_WEB_UPLOAD_ENDPOINT = "/api/upload-dataset.php"
    SC_WEB_STATUS_ENDPOINT = "/api/upload-status.php"
    
    # Test files
    NEXUS_4D_FILE = "/path/to/file.nxs"
    TIFF_RGB_FILE = "/path/to/file.tif"
    IDX_FILE = "/path/to/file.zip"
    
    # Test settings
    USER_EMAIL = "amy@visus.net"
    MAX_WAIT_TIME = 300
```

## Differences from SCLib Tests

| Feature | SCLib Tests | SC_Web E2E Tests |
|---------|-------------|------------------|
| **Target** | FastAPI directly | PHP proxy layer |
| **Authentication** | Not tested | Tested |
| **Error Handling** | FastAPI errors | PHP + FastAPI errors |
| **Response Parsing** | FastAPI JSON | PHP JSON parsing |
| **User Flow** | API level | Full user workflow |

## Common Bugs This Catches

1. **PHP Response Parsing**: Invalid JSON from FastAPI
2. **Authentication Issues**: Session handling problems
3. **Error Propagation**: Errors not properly forwarded
4. **Status Polling**: Status endpoint bugs
5. **File Upload**: Multipart form data issues
6. **Response Format**: Unexpected response structures

## Example Output

```
============================================================
Test: 4D Nexus Upload via SC_Web
File: /path/to/file.nxs
============================================================
Uploading file through SC_Web...
✅ Upload initiated through SC_Web!
   Job ID: upload_abc123
   Response: {'job_id': 'upload_abc123', 'status': 'queued'}
Waiting for upload and conversion to complete...
  Status: None -> queued (0.0%)
  Status: queued -> uploading (25.5%)
  Status: uploading -> processing (100.0%)
  Status: processing -> completed (100.0%)
✅ 4D Nexus upload completed successfully!
   Dataset: AUTO_TEST_4D_NEXUS_20240101_120000
   Final Status: completed
   Progress: 100.0%
```

## Troubleshooting

### SC_Web not accessible
- Verify SC_Web is running: `curl http://localhost`
- Check `SC_WEB_BASE_URL` environment variable
- Ensure network connectivity

### Authentication errors
- You may need to add session cookie handling
- Check `includes/auth.php` for authentication requirements
- May need to login first and capture session cookie

### PHP errors in response
- Check PHP error logs
- Verify FastAPI is accessible from PHP
- Check `SCLIB_UPLOAD_URL` environment variable in PHP

### Response parsing errors
- This is exactly what this test suite is designed to catch!
- Check `upload-dataset.php` for JSON parsing issues
- Verify FastAPI returns valid JSON

## Integration with CI/CD

```yaml
# Example GitHub Actions
- name: Run SC_Web E2E Tests
  env:
    SC_WEB_BASE_URL: http://localhost
  run: |
    cd scientistcloud/SC_Web/tests
    pytest test_upload_e2e.py -v
```

## Next Steps

1. **Add Authentication**: Implement session cookie handling for authenticated tests
2. **Add More Error Cases**: Test more error scenarios
3. **Add Remote Uploads**: Test remote link uploads through SC_Web
4. **Add Performance Tests**: Test large file uploads
5. **Add Concurrent Tests**: Test multiple simultaneous uploads

## Related Files

- `test_upload_e2e.py`: Main E2E test suite
- `test_upload_config.py`: Configuration
- `../api/upload-dataset.php`: PHP upload proxy
- `../api/upload-status.php`: PHP status proxy
- `../assets/js/upload-manager.js`: Frontend upload code

