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
    && docker-php-ext-install pdo_mysql mbstring exif pcntl bcmath gd zip

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Enable Apache modules
RUN a2enmod rewrite headers

# Application files will be mounted via volume in docker-compose.yml
# No need to copy - they're mounted from ../SC_Web/

# Set proper permissions
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# Create logs directory
RUN mkdir -p /var/www/html/logs \
    && chown -R www-data:www-data /var/www/html/logs

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

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Apache in the background\n\
apache2-foreground &\n\
\n\
# Keep container running\n\
wait' > /start.sh && chmod +x /start.sh

# Expose port 8080 (different from main site)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/test-simple.php || exit 1

# Start the application
CMD ["/start.sh"]
