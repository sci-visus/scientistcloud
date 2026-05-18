# Auth0 Setup for ScientistCloud

This document describes the Auth0 integration that has been implemented for ScientistCloud.

## Files Created/Modified

### New Files:
- `config_auth0.php` - Auth0 configuration and SDK initialization
- `auth/callback.php` - Auth0 callback handler for login flow
- `signup.php` - Database (email/password) sign-up entry point
- `login_verification_sent.php` - Post sign-up “check your email” page
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

1. **Allowed Callback URLs** (comma-separated):
   ```
   https://scientistcloud.com/portal/auth/callback.php
   http://51.81.155.171/portal/auth/callback.php
   ```

2. **Allowed Logout URLs**:
   ```
   https://scientistcloud.com/portal/login.php
   https://scientistcloud.com/portal/signup.php
   ```

3. **Allowed Web Origins (CORS)**:
   ```
   https://scientistcloud.com
   ```

4. **Application Type**: Regular Web Application (not SPA)

5. **Connections** (Applications → your app → Connections):
   - Enable **Username-Password-Authentication** (email/password sign-up)
   - Enable **google-oauth2** (Google sign-in)

### Database sign-up (email + password)

Google can work while database sign-up returns **400** on `dev-ep26akpb.auth0.com/u/signup`. Fix this in Auth0, not in PHP.

1. **Authentication → Database → Username-Password-Authentication → Settings**
   - **Disable Sign Ups** must be **off** (sign-ups allowed).

2. **Applications → your app → Connections**
   - **Username-Password-Authentication** enabled for this application.

3. **Branding / Email templates**
   - Do not redirect verification to legacy `http://51.81.155.171/login_error.php`.
   - **Redirect To** after sign-up: `https://scientistcloud.com/portal/login_verification_sent.php?signup=1`
   - **Requires Email Verification** on the database connection must be **ON** or Auth0 will not send mail.
   - **Branding → Email Provider** must be configured (built-in or SMTP).
   - If logs show `451 Authentication failed: Maximum credits exceeded`, the built-in Auth0 mail quota is exhausted — switch to **Use my own email provider** (SendGrid, SES, Mailgun, etc.).

4. **Management API** (resend verification on portal)
   - Set `AUTH0_MANAGEMENT_CLIENT_ID` and `AUTH0_MANAGEMENT_CLIENT_SECRET` on the portal container (see `env.scientistcloud`).
   - Machine-to-machine app needs scope `create:users` and `update:users` (or send verification email permission).

5. **Security → Attack Protection**
   - Bot/CAPTCHA challenges often fail in Safari (TrustedHTML / Cloudflare console errors → 400 on signup). Test in Chrome or relax attack protection while debugging.

6. **Portal sign-up entry point** (after deploy):
   `https://scientistcloud.com/portal/signup.php`  
   Uses `screen_hint=signup` and `connection=Username-Password-Authentication`.

7. **Monitoring → Logs** in Auth0: inspect failed signup events for the exact 400 reason.

### Scopes
   - `openid`, `profile`, `email`, `offline_access`
   - `https://www.googleapis.com/auth/drive.readonly` (optional)

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
