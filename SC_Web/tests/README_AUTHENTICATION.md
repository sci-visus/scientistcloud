# Authentication for SC_Web Tests

SC_Web requires authentication via Auth0 before uploads can be tested. Currently, the tests will get **401 authentication errors**, which is expected behavior.

## Current Test Behavior

- ✅ Tests connect to SC_Web successfully
- ✅ Tests validate that PHP proxy responds correctly
- ⚠️  Tests get 401 errors (authentication required) - this is **correct behavior**

## Why 401 is Expected

SC_Web's `upload-dataset.php` checks authentication **before** checking for files:

```php
if (!isAuthenticated()) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Authentication required']);
    exit;
}
```

This means:
- **401 = Authentication required** (correct behavior)
- **400 = Missing file** (only reached if authenticated)

## Options for Full Testing

### Option 1: Manual Session Cookie (Quick Testing)

1. Login to SC_Web in browser: `http://localhost:8080`
2. Get session cookie from browser dev tools
3. Set environment variable:
   ```bash
   export SC_WEB_SESSION_COOKIE="your_phpsessid_value"
   ```

### Option 2: Add Authentication Helper (Future Enhancement)

Add a helper function that:
1. Uses Auth0 API to get tokens
2. Creates PHP session via callback
3. Captures PHPSESSID cookie
4. Passes cookie to test client

### Option 3: Test Without Authentication (Current)

Current tests validate:
- ✅ PHP proxy is accessible
- ✅ PHP proxy returns proper JSON errors
- ✅ Error handling works (401 for unauthenticated requests)

## Running Tests

```bash
# Tests will show 401 errors - this is expected
pytest test_upload_e2e.py::TestSCWebErrorHandling -v

# To see what happens with authentication, manually login first
# then tests will show actual file validation errors
```

## What the Tests Validate

Even with 401 errors, the tests validate:

1. **Connection**: SC_Web is accessible
2. **Response Format**: PHP returns valid JSON
3. **Error Handling**: Proper error codes and messages
4. **PHP Proxy**: The proxy layer is working correctly

## Next Steps

To test actual upload functionality, you would need to:
1. Implement Auth0 authentication flow in tests
2. Or use a test user with pre-authenticated session
3. Or add a test mode that bypasses auth (requires PHP changes)

For now, the tests successfully validate that the **PHP proxy layer is working correctly**, even if authentication is required.

