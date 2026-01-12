#!/bin/bash
# Script to fix dashboard and Composer dependency issues
# Run this on the remote server

set -e

echo "🔧 Fixing Dashboard and Composer Issues"
echo "========================================"
echo ""

# 1. Check PHP error logs
echo "1️⃣ Checking PHP error logs..."
docker logs scientistcloud-portal 2>&1 | grep -i error | tail -20
echo ""

# 2. Test the dashboards API
echo "2️⃣ Testing dashboards API..."
curl -s https://scientistcloud.com/portal/api/dashboards.php | head -50
echo ""
echo ""

# 3. Fix Composer dependencies
echo "3️⃣ Fixing Composer dependencies..."
echo "   Entering portal container..."
docker exec scientistcloud-portal bash -c "
    cd /var/www/html && \
    echo '📦 Checking composer.json...' && \
    if [ ! -f composer.json ]; then
        echo '⚠️ composer.json not found, creating from template...'
        echo '{\"require\":{\"php\":\">=8.0\",\"auth0/auth0-php\":\"^8.17\",\"guzzlehttp/guzzle\":\"^7.0\",\"guzzlehttp/psr7\":\"^2.0\",\"guzzlehttp/promises\":\"^2.0\",\"php-http/discovery\":\"^1.19\",\"psr/http-factory\":\"^1.0\",\"psr/http-client\":\"^1.0\"},\"config\":{\"optimize-autoloader\":true,\"sort-packages\":true,\"allow-plugins\":{\"php-http/discovery\":true}},\"minimum-stability\":\"stable\",\"prefer-stable\":true}' > composer.json
    fi && \
    echo '📦 Updating composer dependencies...' && \
    composer update --no-dev --optimize-autoloader --no-interaction --prefer-dist && \
    echo '✅ Composer update complete' && \
    echo '📦 Regenerating autoloader...' && \
    composer dump-autoload --optimize --no-interaction && \
    echo '✅ Autoloader regenerated' && \
    echo '🔍 Verifying PSR-17 factory (GuzzleHttp)...' && \
    php -r \"require 'vendor/autoload.php'; if (class_exists('GuzzleHttp\\\\Psr7\\\\HttpFactory')) { \\\$factory = new \\GuzzleHttp\\Psr7\\HttpFactory(); echo '✅ PSR-17 factory found: ' . get_class(\\\$factory) . PHP_EOL; } else { echo '⚠️ GuzzleHttp\\\\Psr7\\\\HttpFactory not found' . PHP_EOL; }\" || echo '⚠️ PSR-17 verification failed'
"
echo ""

# 4. Restart portal container
echo "4️⃣ Restarting portal container..."
docker restart scientistcloud-portal
echo "✅ Portal container restarted"
echo ""

# 5. Wait and test again
echo "5️⃣ Waiting for portal to start (10 seconds)..."
sleep 10

echo "6️⃣ Testing dashboards API again..."
curl -s https://scientistcloud.com/portal/api/dashboards.php | python3 -m json.tool 2>/dev/null | head -30 || curl -s https://scientistcloud.com/portal/api/dashboards.php | head -50
echo ""

echo "✅ Fix script complete!"
echo ""
echo "Next steps:"
echo "  - Check browser console for JavaScript errors"
echo "  - Verify dashboards load in the portal"
echo "  - Check error banner appears if there are issues"

