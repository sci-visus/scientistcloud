# Auth0 Setup for ScientistCloud

This document describes the Auth0 integration that has been implemented for ScientistCloud.

## Files Created/Modified

### New Files:
- `config_auth0.php` - Auth0 configuration and SDK initialization
- `auth/callback.php` - Auth0 callback handler for login flow
- `logout.php` - Logout page with Auth0 integration
- `AUTH0_SETUP.md` - This documentation file

### Modified Files:
- `login.php` - Updated to use Auth0 instead of form-based authentication
- `includes/auth.php` - Enhanced with Auth0 session management

## Configuration Required

### Environment Variables
Make sure these environment variables are set in your ScientistCloud configuration:

```bash
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
```

### Auth0 Application Settings
In your Auth0 dashboard (https://manage.auth0.com/dashboard), configure:

1. **Allowed Callback URLs**: Add these URLs (comma-separated):
   ```
   https://scientistcloud.com/portal/auth/callback.php
   https://scientistcloud.com/auth/callback.php
   ```
   
2. **Allowed Logout URLs**: Add these URLs:
   ```
   https://scientistcloud.com/portal/login.php
   https://scientistcloud.com/login.php
   ```

3. **Allowed Web Origins (CORS)**: Add:
   ```
   https://scientistcloud.com
   ```

4. **Application Type**: Set to "Regular Web Application" (not SPA)

5. **Scopes**: Ensure these scopes are enabled:
   - `openid`
   - `profile`
   - `email`
   - `offline_access`
   - `https://www.googleapis.com/auth/drive`

### Auth0 API Configuration (Optional)

If you're using an Auth0 API (for protected API endpoints), you need to:

1. **Create an API in Auth0 Dashboard** (if it doesn't exist):
   - Go to APIs section in Auth0 dashboard
   - Create a new API or use an existing one
   - Note the API Identifier (audience)
   - Set this in your `AUTH0_AUDIENCE` environment variable

2. **If NOT using an Auth0 API** (just authentication):
   - Set `AUTH0_AUDIENCE` to empty/null in your environment
   - The code will automatically use `null` for audience (no API access)

## How It Works

1. **Login Flow**:
   - User visits `/login.php`
   - If not authenticated, redirects to Auth0 login
   - Auth0 handles authentication and redirects to `/auth/callback.php`
   - Callback creates/updates user in SCLib system
   - User is redirected to main application

2. **Session Management**:
   - Auth0 tokens are stored in PHP session
   - User profile is managed through SCLib API
   - Session includes user ID, email, name, and Auth0 ID

3. **Logout Flow**:
   - User visits `/logout.php`
   - Session is cleared
   - Redirects to Auth0 logout URL
   - Auth0 handles logout and redirects back to login page

## Dependencies

- Auth0 PHP SDK (installed via Composer)
- SCLib API for user management
- PHP sessions for state management

## Quick Setup Checklist

### In Auth0 Dashboard (https://manage.auth0.com/dashboard):

1. Go to **Applications** → Your Application
2. Under **Application URIs**, add:
   - **Allowed Callback URLs**: 
     ```
     https://scientistcloud.com/portal/auth/callback.php
     ```
   - **Allowed Logout URLs**: 
     ```
     https://scientistcloud.com/portal/login.php
     ```
   - **Allowed Web Origins (CORS)**: 
     ```
     https://scientistcloud.com
     ```

3. **Important**: If you get "Service not found" error about audience:
   - Either create an API in Auth0 with identifier matching `AUTH0_AUDIENCE` env var
   - OR set `AUTH0_AUDIENCE` to empty/null in your environment to disable API access

## Testing

1. Visit `https://scientistcloud.com/portal/login.php` - should redirect to Auth0
2. Complete Auth0 login - should redirect back to portal
3. Visit `https://scientistcloud.com/portal/logout.php` - should clear session and redirect to Auth0 logout
4. Check that user data is properly stored in SCLib system

## Troubleshooting

### Error: "Service not found: https://scientistcloud.com"
- **Cause**: Auth0 is looking for an API with that identifier, but it doesn't exist
- **Solution**: Set `AUTH0_AUDIENCE` to empty/null in your env file, or create the API in Auth0

### Error: "Invalid redirect URI"
- **Cause**: The callback URL isn't in Auth0's allowed list
- **Solution**: Add `https://scientistcloud.com/portal/auth/callback.php` to Allowed Callback URLs

### Error: "access_denied" 
- **Cause**: Usually means the callback URL isn't configured correctly in Auth0
- **Solution**: Verify Allowed Callback URLs includes the portal path

### Other Issues
- Check Auth0 application settings match the callback URLs
- Verify environment variables are set correctly  
- Check SCLib API is running and accessible
- Review application logs: `docker logs scientistcloud-portal`
