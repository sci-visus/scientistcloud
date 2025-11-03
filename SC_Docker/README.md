# ScientistCloud Data Portal - Docker Setup

This Docker configuration sets up the ScientistCloud Data Portal with integrated SCLib support.

## Features

- **PHP 8.2** with Apache web server
- **Python 3** support for SCLib integration
- **MongoDB** connectivity
- **Auth0** authentication
- **Google OAuth** integration
- **SCLib** job processing system

## Quick Start

1. **Copy environment template:**
   ```bash
   cp env.template .env
   ```
   or 
   ```
   cp ../../SCLib_TryTest/env.scientistcloud .env
   ```

2. **Edit .env file** with your configuration values

3. **Start the portal:**
   ```bash
   ./start.sh
   ```

4. **Access the portal:**
   - Portal: http://localhost:8080
   - Test config: http://localhost:8080/test-config.php

## Configuration

### Environment Variables

The following environment variables need to be configured in your `.env` file:

#### Database
- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name
- `DB_HOST`: Database host
- `DB_PASS`: Database password

#### Authentication
- `AUTH0_DOMAIN`: Auth0 domain
- `AUTH0_CLIENT_ID`: Auth0 client ID
- `AUTH0_CLIENT_SECRET`: Auth0 client secret
- `AUTH0_MANAGEMENT_CLIENT_ID`: Auth0 management client ID
- `AUTH0_MANAGEMENT_CLIENT_SECRET`: Auth0 management client secret

#### Google OAuth
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `AUTH_GOOGLE_CLIENT_ID`: Auth Google client ID
- `AUTH_GOOGLE_CLIENT_SECRET`: Auth Google client secret

#### Security
- `SECRET_KEY`: Application secret key
- `SECRET_IV`: Application secret IV

#### Server
- `DEPLOY_SERVER`: Server URL
- `DOMAIN_NAME`: Domain name

#### File Paths
- `VISUS_DB`: Visus database path
- `VISUS_DATASETS`: Visus datasets path
- `HOME_DIR`: Home directory path

## File Structure

```
SC_Docker/
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # PHP/Python container definition
├── env.template               # Environment variables template
├── README.md                  # This file
└── logs/                      # Application logs (created automatically)
```

## Volumes

The following volumes are mounted:

- `../SC_Web` → `/var/www/html` (Portal web files)
- `../../scientistCloudLib` → `/var/www/scientistCloudLib` (SCLib system)
- `./logs` → `/var/www/html/logs` (Application logs)
- `./config` → `/var/www/html/config` (Configuration files)

## Testing

1. **Configuration Test:**
   Visit http://localhost:8080/test-config.php to verify:
   - SCLib files are accessible
   - Configuration loads correctly
   - Environment variables are set
   - Database connection works

2. **Simple Test:**
   Visit http://localhost:8080/test-simple.php for basic PHP functionality

## Troubleshooting

### Common Issues

1. **"Failed to open stream" error:**
   - Check that SCLib files are mounted correctly
   - Verify paths in config.php
   - Ensure SCLib_Config.php exists

2. **Database connection errors:**
   - Verify MongoDB is running
   - Check MONGO_URL in .env file
   - Ensure database credentials are correct

3. **Authentication errors:**
   - Verify Auth0 configuration
   - Check client IDs and secrets
   - Ensure Auth0 domain is correct

### Logs

Check application logs in the `logs/` directory:
```bash
docker-compose logs scientistcloud-portal
```

## Development

### Adding New Features

1. **PHP Files:** Add to `../SC_Web/`
2. **SCLib Integration:** Add to `../../scientistCloudLib/`
3. **Configuration:** Update `config.php`

### Testing Changes

```bash
# Rebuild container
docker-compose up --build

# Check logs
docker-compose logs -f scientistcloud-portal
```

## Production Deployment

1. **Security:**
   - Use strong secret keys
   - Enable HTTPS
   - Configure proper CORS settings

2. **Performance:**
   - Adjust PHP memory limits
   - Configure Apache for production
   - Set up proper logging

3. **Monitoring:**
   - Set up health checks
   - Monitor application logs
   - Configure alerts

## Support

For issues and questions:
1. Check the test-config.php page
2. Review Docker logs
3. Verify environment configuration
4. Check SCLib integration status


## Errors:

docker exec -it scientistcloud-portal bash -c "cd /var/www/html && composer update guzzlehttp/guzzle --no-dev --optimize-autoloader && composer dump-autoload --optimize"