# Authentication for E2E Tests

SC_Web requires authentication via Auth0. To run the full E2E tests (including conversion tests), you need to provide a valid session cookie.

## How Authentication Works

1. **User logs in** via Auth0 OAuth flow at `http://localhost:8080/login.php`
2. **Auth0 authenticates** the user and redirects back to SC_Web
3. **SC_Web creates a PHP session** and sets a `PHPSESSID` cookie
4. **Tests use this cookie** to authenticate requests

## Getting the Session Cookie

### Method 1: Manual (Recommended)

1. **Login to SC_Web**:
   ```bash
   # Open in browser
   open http://localhost:8080/login.php
   # Or visit: http://localhost:8080/login.php
   ```

2. **Complete Auth0 login** (enter credentials, authorize, etc.)

3. **After successful login**, open browser DevTools:
   - Press `F12` (or right-click → Inspect)
   - Go to **Application** tab (Chrome) or **Storage** tab (Firefox)
   - Expand **Cookies** → `http://localhost:8080`
   - Find **PHPSESSID** cookie
   - Copy its **Value**

4. **Export the cookie**:
   ```bash
   export SC_WEB_SESSION_COOKIE="<paste_cookie_value_here>"
   ```

5. **Run tests**:
   ```bash
   pytest test_upload_e2e.py -v
   ```

### Method 2: Using Helper Script

```bash
# Run helper script (opens browser for you)
python get_session_cookie.py

# Then follow steps 3-5 from Method 1 above
```

## Cookie Format

The cookie value should look something like:
```
abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

It's a long alphanumeric string (typically 26-32 characters for PHP sessions).

## Important Notes

- **PHPSESSID vs Auth0 cookies**: SC_Web uses PHP's `PHPSESSID` cookie, not Auth0 session cookies directly. The PHP session is created after Auth0 authentication.

- **Cookie expiration**: PHP sessions typically expire after 24 minutes of inactivity. If tests fail with 401 errors, you may need to get a fresh cookie.

- **Related code**: This is similar to how `utils_bokeh_auth.py` handles authentication for Bokeh dashboards, but for E2E tests we need the PHP session cookie from SC_Web.

## Testing Without Authentication

If you don't provide a cookie, tests will:
- ✅ Still run
- ⚠️ Skip tests that require authentication (with clear messages)
- ✅ Validate that the PHP proxy correctly returns 401 errors

This is useful for:
- Testing error handling
- Validating that authentication is enforced
- CI/CD pipelines where you might not have interactive login

## Troubleshooting

### "401 Unauthorized" errors
- **Cause**: Cookie expired or invalid
- **Fix**: Get a fresh cookie (login again and copy new PHPSESSID)

### "Could not connect to SC_Web"
- **Cause**: SC_Web container not running
- **Fix**: Start SC_Web: `docker ps | grep scientistcloud-portal`

### Cookie not working
- **Check**: Cookie value is correct (no extra spaces, quotes, etc.)
- **Check**: Cookie is for the correct domain (localhost:8080)
- **Check**: Session hasn't expired (login again)

## Example

```bash
# 1. Get cookie (see steps above)
export SC_WEB_SESSION_COOKIE="abc123def456ghi789..."

# 2. Run all tests
pytest test_upload_e2e.py -v

# 3. Run specific test class
pytest test_upload_e2e.py::TestSCWebConversion -v

# 4. Run specific test
pytest test_upload_e2e.py::TestSCWebConversion::test_scweb_conversion_status_transitions -v
```
