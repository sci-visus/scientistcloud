# ScientistCloud Data Portal - Docker Container
FROM php:8.2-apache

# Set working directory
WORKDIR /var/www/html

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    libpng-dev \
    libonig-dev \
    libxml2-dev \
    libzip-dev \
    zip \
    unzip \
    python3 \
    python3-pip \
    python3-dev \
    pkg-config \
    libssl-dev \
    && docker-php-ext-install pdo_mysql mbstring exif pcntl bcmath gd zip

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Install PHP dependencies for Auth0 (PSR-17 HTTP Factory and PSR-18 HTTP Client)
# Install Guzzle HTTP which provides PSR-17 factories globally as backup
RUN composer global require guzzlehttp/guzzle:^7.0 guzzlehttp/psr7:^2.0 php-http/discovery:^1.19 || true

# Create a minimal composer.json for build-time dependency installation
# Note: SC_Web directory (with full composer.json) will be mounted as volume at runtime
RUN echo '{"require":{"php":">=8.0","auth0/auth0-php":"^8.17","guzzlehttp/guzzle":"^7.0","guzzlehttp/psr7":"^2.0","php-http/discovery":"^1.19"},"config":{"optimize-autoloader":true,"sort-packages":true},"minimum-stability":"stable","prefer-stable":true}' > /var/www/html/composer.json

# Install dependencies during build (these will be available even if volume overwrites vendor)
# The vendor directory in the volume will be used at runtime if it exists
RUN cd /var/www/html && \
    composer install --no-dev --optimize-autoloader --no-interaction

# No MongoDB dependencies needed - using SCLib API for all database operations

# Install Python dependencies for SCLib
# Use --break-system-packages to override externally-managed-environment restriction
RUN pip3 install --break-system-packages --no-cache-dir \
    pymongo \
    fastapi \
    uvicorn \
    flask \
    flask-cors \
    python-multipart \
    python-jose[cryptography] \
    passlib[bcrypt] \
    python-dotenv \
    requests \
    pydantic \
    email-validator

# Enable Apache modules
RUN a2enmod rewrite headers

# Application files will be mounted via volume in docker-compose.yml
# No need to copy - they're mounted from ../SC_Web/

# Set proper permissions
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# Create logs directory with proper permissions
RUN mkdir -p /var/www/html/logs \
    && chown -R www-data:www-data /var/www/html/logs \
    && chmod -R 775 /var/www/html/logs

# Configure Apache
RUN echo '<VirtualHost *:80>\n\
    DocumentRoot /var/www/html\n\
    ServerName scientistcloud.com\n\
    ServerAlias www.scientistcloud.com\n\
    \n\
    <Directory /var/www/html>\n\
        AllowOverride All\n\
        Require all granted\n\
    </Directory>\n\
    \n\
    # Custom error pages\n\
    ErrorDocument 404 /404.html\n\
    ErrorDocument 500 /500.html\n\
    \n\
    # Security headers\n\
    Header always set X-Content-Type-Options nosniff\n\
    Header always set X-Frame-Options DENY\n\
    Header always set X-XSS-Protection "1; mode=block"\n\
    \n\
    # CORS headers for API\n\
    Header always set Access-Control-Allow-Origin "*"\n\
    Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"\n\
    Header always set Access-Control-Allow-Headers "Content-Type, Authorization"\n\
</VirtualHost>' > /etc/apache2/sites-available/000-default.conf

# Configure PHP
RUN echo 'memory_limit = 2G\n\
max_execution_time = 300\n\
upload_max_filesize = 500M\n\
post_max_size = 500M\n\
max_input_vars = 3000\n\
date.timezone = UTC\n\
session.cookie_httponly = 1\n\
session.cookie_secure = 0\n\
session.use_strict_mode = 1' > /usr/local/etc/php/conf.d/custom.ini

# Verify SCLib API connectivity (no MongoDB dependencies needed)
RUN echo "Portal configured to use SCLib API - no direct database access"

# Configure Apache to listen on port 8080
RUN echo 'Listen 8080\n\
ServerName scientistcloud.com\n\
<VirtualHost *:8080>\n\
    DocumentRoot /var/www/html\n\
    ServerName scientistcloud.com\n\
    <Directory /var/www/html>\n\
        AllowOverride All\n\
        Require all granted\n\
    </Directory>\n\
</VirtualHost>' > /etc/apache2/sites-available/000-default.conf

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting ScientistCloud Portal..."\n\
\n\
# Always check and ensure dependencies are properly installed\n\
cd /var/www/html\n\
\n\
if [ -f composer.json ]; then\n\
    echo "📦 Checking dependencies..."\n\
    \n\
    # Check if autoload exists and if key packages are installed\n\
    if [ ! -f vendor/autoload.php ] || [ ! -d vendor/guzzlehttp ] || [ ! -d vendor/php-http ]; then\n\
        echo "📥 Installing/updating dependencies from composer.json..."\n\
        composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist\n\
        echo "✅ Dependencies installed"\n\
    else\n\
        echo "📋 Dependencies found, updating autoload..."\n\
        composer dump-autoload --optimize --no-interaction 2>/dev/null || true\n\
    fi\n\
    \n\
    # Verify critical packages exist\n\
    if [ ! -d vendor/auth0 ] || [ ! -d vendor/guzzlehttp/guzzle ]; then\n\
        echo "⚠️ Missing critical packages, forcing reinstall..."\n\
        composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist\n\
    fi\n\
else\n\
    echo "⚠️ composer.json not found, creating minimal one..."\n\
    echo '"'"'{"require":{"php":">=8.0","auth0/auth0-php":"^8.17","guzzlehttp/guzzle":"^7.0","guzzlehttp/psr7":"^2.0","php-http/discovery":"^1.19"},"config":{"optimize-autoloader":true,"sort-packages":true},"minimum-stability":"stable","prefer-stable":true}'"'"' > composer.json\n\
    composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist\n\
    echo "✅ Minimal dependencies installed"\n\
fi\n\
\n\
# Verify PSR-17 factory discovery works\n\
echo "🔍 Verifying PSR-17 factory..."\n\
cd /var/www/html && php -r "require '"'"'vendor/autoload.php'"'"'; try { \$discovery = new \\Psr\\Discovery\\HttpFactoryDiscovery(); \$factory = \$discovery->findRequestFactory(); echo \"✅ PSR-17 factory found: \" . get_class(\$factory) . \"\\n\"; } catch (Exception \$e) { echo \"❌ PSR-17 factory error: \" . \$e->getMessage() . \"\\n\"; exit(1); }" || {\n\
    echo "⚠️ PSR-17 factory verification failed, but continuing..."\n\
    echo "   This might cause Auth0 SDK issues. Check that guzzlehttp/guzzle and php-http/discovery are installed."\n\
}\n\
\n\
echo "✅ Startup checks complete"\n\
echo "🌐 Starting Apache..."\n\
\n\
# Start Apache in the foreground\n\
exec apache2-foreground' > /start.sh && chmod +x /start.sh

# Expose port 8080 (different from main site)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/test-simple.php || exit 1

# Start the application
CMD ["/start.sh"]
