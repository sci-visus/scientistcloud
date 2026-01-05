# Authentication API

The ScientistCloud API uses JWT (JSON Web Token) authentication. This guide explains how to authenticate and use tokens.

## Overview

Authentication is a two-step process:

1. **Login**: Exchange your email for an access token
2. **Use Token**: Include the token in API requests

## Login Endpoint

### POST `/api/auth/login`

Login with your email address to receive an access token.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}'
```

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 86400,
    "token_type": "Bearer",
    "user": {
      "user_id": "user_abc123",
      "email": "user@example.com",
      "name": "User Name",
      "email_verified": true
    }
  }
}
```

**Extract Token:**

```bash
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')
```

## Using the Token

Include the token in the `Authorization` header for all authenticated requests:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/status"
```

## Check Authentication Status

### GET `/api/auth/status`

Verify that your token is valid.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/status"
```

**Response:**

```json
{
  "success": true,
  "message": "Token is valid",
  "user": {
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

## Get Current User Info

### GET `/api/auth/me`

Get information about the authenticated user.

**Request:**

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/me"
```

**Response:**

```json
{
  "success": true,
  "user": {
    "user_id": "user_abc123",
    "email": "user@example.com",
    "name": "User Name",
    "email_verified": true
  }
}
```

## Refresh Token

### POST `/api/auth/refresh`

Refresh an expired access token using a refresh token.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/api/auth/refresh" \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

**Response:**

```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 86400,
    "token_type": "Bearer"
  }
}
```

## Logout

### POST `/api/auth/logout`

Logout and revoke the current token.

**Request:**

```bash
curl -X POST "https://scientistcloud.com/api/auth/logout" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json"
```

**Response:**

```json
{
  "success": true,
  "message": "Logout successful"
}
```

## Token Expiration

- **Access tokens** expire after **24 hours**
- **Refresh tokens** expire after **30 days**

When a token expires, you'll receive a `401 Unauthorized` response. Simply login again to get a new token.

## Error Responses

### Invalid Credentials

```json
{
  "success": false,
  "error": "Invalid email or authentication failed",
  "code": "AUTH_ERROR"
}
```

### Expired Token

```json
{
  "success": false,
  "error": "Token has expired",
  "code": "TOKEN_EXPIRED"
}
```

### Missing Token

```json
{
  "success": false,
  "error": "Authentication required",
  "code": "AUTH_REQUIRED"
}
```

## Complete Example

```bash
#!/bin/bash

# 1. Login
echo "Logging in..."
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Login failed"
    exit 1
fi

echo "✅ Token obtained: ${TOKEN:0:20}..."

# 2. Verify token
echo "Verifying token..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/status" | jq

# 3. Get user info
echo "Getting user info..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/me" | jq

# 4. Use token for API calls
echo "Listing datasets..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/portal/api/datasets" | jq

# 5. Logout
echo "Logging out..."
curl -s -X POST "https://scientistcloud.com/api/auth/logout" \
     -H "Authorization: Bearer $TOKEN" | jq
```

## Best Practices

1. **Store tokens securely**: Don't hardcode tokens in scripts or commit them to version control
2. **Handle expiration**: Check for 401 errors and re-authenticate when needed
3. **Use environment variables**: Store tokens in environment variables
4. **Logout when done**: Explicitly logout to revoke tokens when finished

## Troubleshooting

### Token Not Working

```bash
# Check if token is valid
curl -H "Authorization: Bearer $TOKEN" \
     "https://scientistcloud.com/api/auth/status"

# If expired, login again
TOKEN=$(curl -s -X POST "https://scientistcloud.com/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}' | \
     jq -r '.data.access_token')
```

### Authentication Service Down

```bash
# Check service health
curl https://scientistcloud.com/api/auth/health

# Should return: {"status": "healthy"}
```

## Next Steps

- See [Upload API](?page=api-upload) for authenticated uploads
- Check [Curl Scripts](?page=curl-scripts) for complete examples
- Review [Python Examples](?page=python-examples) for programmatic access

