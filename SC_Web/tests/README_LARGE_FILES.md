# Large File Upload Testing

## Overview

The E2E test suite supports testing large file uploads (GB to TB sized files), but there are some limitations when running tests from the host machine.

## Production System

**Your production system CAN handle large files** through the following mechanisms:

1. **FastAPI Chunked Upload API**: The FastAPI backend (`sclib_fastapi`) supports chunked uploads for files > 100MB
   - Chunk size: 100MB
   - Supports files up to 10TB
   - Endpoints: `/api/upload/large/initiate`, `/api/upload/large/chunk/{upload_id}/{chunk_index}`, `/api/upload/large/complete/{upload_id}`

2. **Frontend JavaScript**: The `upload-manager.js` can be enhanced to use chunked uploads for large files
   - Currently uses standard upload through PHP proxy
   - Can be modified to detect large files and use FastAPI chunked upload API directly

3. **PHP Proxy**: The `upload-dataset.php` proxy forwards to FastAPI
   - Has a 5-minute timeout (300 seconds)
   - Suitable for files < ~500MB at typical upload speeds
   - For larger files, consider direct FastAPI chunked upload API

## Testing Limitations

### Host Machine Testing

When running tests from the host machine (outside Docker):

- **FastAPI may not be accessible**: If FastAPI port 5001 is not exposed to the host, tests will fall back to PHP proxy
- **PHP proxy timeout**: 5-minute timeout limits testable file sizes
- **Recommendation**: Use smaller test files (< 500MB) for E2E tests

### Docker Network Testing

If you need to test large files:

1. **Expose FastAPI port** in docker-compose.yml:
   ```yaml
   sclib_fastapi:
     ports:
       - "5001:5001"
   ```

2. **Or run tests from within Docker network**:
   ```bash
   docker exec -it scientistcloud-portal bash
   # Then run tests from inside container
   ```

## Test File Size Recommendations

| File Size | Test Method | Expected Behavior |
|-----------|-------------|-------------------|
| < 100MB | Standard upload via PHP proxy | ✅ Works reliably |
| 100MB - 500MB | Standard upload via PHP proxy | ⚠️ May timeout depending on network speed |
| 500MB - 1GB | Standard upload via PHP proxy | ❌ Will likely timeout |
| > 1GB | Chunked upload via FastAPI (if accessible) | ✅ Works if FastAPI is accessible |
| > 1GB | Standard upload via PHP proxy (fallback) | ❌ Will timeout |

## Production Recommendations

For production handling of large files:

1. **Frontend Enhancement**: Modify `upload-manager.js` to:
   - Detect files > 100MB
   - Use FastAPI chunked upload API directly (bypass PHP proxy)
   - Show progress during chunked uploads

2. **PHP Proxy Enhancement** (optional):
   - Increase timeout for large files
   - Or proxy chunked upload requests to FastAPI

3. **FastAPI Access**: Ensure FastAPI is accessible from frontend
   - Either expose port 5001
   - Or use nginx reverse proxy to route chunked upload requests

## Current Test Behavior

The test suite (`test_upload_e2e.py`) will:

1. **For files > 1GB**:
   - Try to use FastAPI chunked upload API if accessible
   - Fall back to PHP proxy if FastAPI not accessible
   - Warn about potential timeout

2. **For files < 1GB**:
   - Use standard upload via PHP proxy
   - Calculate dynamic timeout based on file size

## Example: Testing Large Files

```python
# This will work if FastAPI is accessible from host
result = sc_web_client.upload_file(
    file_path="/path/to/large/file.nxs",  # 4GB file
    user_email="user@example.com",
    dataset_name="Large Dataset",
    sensor="4D_NEXUS",
    convert=True
)
# Will use chunked upload if FastAPI accessible
# Will fall back to PHP proxy (and likely timeout) if not
```

## Production System Verification

To verify your production system handles large files:

1. **Check FastAPI is running**: `docker ps | grep sclib_fastapi`
2. **Check chunked upload endpoints**: Access `/api/upload/large/initiate` via FastAPI
3. **Test with real large file**: Upload a large file through the web UI
4. **Monitor upload progress**: Check job status and conversion progress

## Summary

- ✅ **Production system CAN handle large files** via FastAPI chunked uploads
- ⚠️ **E2E tests have limitations** when FastAPI not accessible from host
- 💡 **Use smaller files for testing** (< 500MB recommended)
- 🔧 **For large file testing**, expose FastAPI port or run tests from Docker network

