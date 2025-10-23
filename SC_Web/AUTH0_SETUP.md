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
In your Auth0 dashboard, configure:

1. **Allowed Callback URLs**: Add `https://your-domain.com/auth/callback.php`
2. **Allowed Logout URLs**: Add `https://your-domain.com/login.php`
3. **Allowed Web Origins**: Add `https://your-domain.com`
4. **Scopes**: Ensure these scopes are enabled:
   - `openid`
   - `profile`
   - `email`
   - `offline_access`
   - `https://www.googleapis.com/auth/drive`

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

## Testing

1. Visit `/login.php` - should redirect to Auth0
2. Complete Auth0 login - should redirect back to main app
3. Visit `/logout.php` - should clear session and redirect to Auth0 logout
4. Check that user data is properly stored in SCLib system

## Troubleshooting

- Check Auth0 application settings match the callback URLs
- Verify environment variables are set correctly
- Check SCLib API is running and accessible
- Review application logs for authentication errors
