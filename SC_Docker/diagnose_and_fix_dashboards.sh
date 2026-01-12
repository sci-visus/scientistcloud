#!/bin/bash
# Comprehensive dashboard diagnostic and fix script
# Run this on the remote server from SC_Docker directory

set -e

echo "🔍 Dashboard Diagnostic and Fix Script"
echo "======================================="
echo ""

# 1. Check if container is running
echo "1️⃣ Checking container status..."
if ! docker ps | grep -q scientistcloud-portal; then
    echo "❌ Container is not running! Starting it..."
    docker-compose up -d scientistcloud-portal || docker start scientistcloud-portal
    sleep 5
fi
echo "✅ Container is running"
echo ""

# 2. Test dashboards API directly
echo "2️⃣ Testing dashboards API endpoint..."
API_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" https://scientistcloud.com/portal/api/dashboards.php)
HTTP_CODE=$(echo "$API_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$API_RESPONSE" | sed '/HTTP_CODE:/d')

echo "   HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ API returned 200"
    echo "   Response preview:"
    echo "$RESPONSE_BODY" | head -20
    # Check if it's valid JSON
    if echo "$RESPONSE_BODY" | python3 -m json.tool >/dev/null 2>&1; then
        echo "   ✅ Response is valid JSON"
        DASHBOARD_COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null || echo "0")
        echo "   📊 Dashboards found: $DASHBOARD_COUNT"
    else
        echo "   ❌ Response is NOT valid JSON!"
        echo "   Full response:"
        echo "$RESPONSE_BODY"
    fi
else
    echo "   ❌ API returned error code: $HTTP_CODE"
    echo "   Response:"
    echo "$RESPONSE_BODY"
fi
echo ""

# 3. Check PHP errors in container
echo "3️⃣ Checking PHP error logs..."
docker exec scientistcloud-portal tail -50 /var/log/apache2/error.log 2>/dev/null | grep -i "error\|fatal\|warning" | tail -20 || echo "   No recent errors in Apache log"
echo ""

# 4. Test PHP directly in container
echo "4️⃣ Testing PHP and Composer in container..."
docker exec scientistcloud-portal bash -c "
    echo '   PHP version:'
    php -v | head -1
    echo '   Composer version:'
    composer --version 2>/dev/null || echo '   ❌ Composer not found'
    echo '   Checking vendor directory:'
    if [ -d /var/www/html/vendor ]; then
        echo '   ✅ vendor directory exists'
        if [ -f /var/www/html/vendor/autoload.php ]; then
            echo '   ✅ autoload.php exists'
        else
            echo '   ❌ autoload.php missing!'
        fi
    else
        echo '   ❌ vendor directory missing!'
    fi
"
echo ""

# 5. Test dashboards.php directly in container
echo "5️⃣ Testing dashboards.php directly in container..."
docker exec scientistcloud-portal bash -c "
    cd /var/www/html && \
    echo '   Testing PHP execution...' && \
    php -r \"require 'config.php'; echo 'Config loaded\n';\" 2>&1 | head -5 || echo '   ⚠️ Config load had issues' && \
    echo '   Testing dashboards.php...' && \
    php api/dashboards.php 2>&1 | head -30
"
echo ""

# 6. Check if dashboards-list.json exists
echo "6️⃣ Checking for dashboards-list.json..."
docker exec scientistcloud-portal bash -c "
    echo '   Checking possible paths:'
    for path in \
        '/var/www/SC_Dashboards/config/dashboards-list.json' \
        '/var/www/html/../SC_Dashboards/config/dashboards-list.json' \
        '/home/amy/ScientistCloud2.0/scientistcloud/SC_Dashboards/config/dashboards-list.json'; do
        if [ -f \"\$path\" ]; then
            echo \"   ✅ Found: \$path\"
            echo \"   File size: \$(stat -c%s \"\$path\" 2>/dev/null || stat -f%z \"\$path\" 2>/dev/null) bytes\"
            echo \"   First 200 chars:\"
            head -c 200 \"\$path\"
            echo ''
            break
        fi
    done
    echo '   (If none found, dashboards-list.json is missing)'
"
echo ""

# 7. Fix Composer dependencies
echo "7️⃣ Fixing Composer dependencies..."
docker exec scientistcloud-portal bash -c "
    cd /var/www/html && \
    if [ ! -f composer.json ]; then
        echo '   ⚠️ composer.json not found, creating...'
        cat > composer.json << 'EOF'
{
    \"require\": {
        \"php\": \">=8.0\",
        \"auth0/auth0-php\": \"^8.17\",
        \"guzzlehttp/guzzle\": \"^7.0\",
        \"guzzlehttp/psr7\": \"^2.0\",
        \"guzzlehttp/promises\": \"^2.0\",
        \"php-http/discovery\": \"^1.19\",
        \"psr/http-factory\": \"^1.0\",
        \"psr/http-client\": \"^1.0\"
    },
    \"config\": {
        \"optimize-autoloader\": true,
        \"sort-packages\": true,
        \"allow-plugins\": {
            \"php-http/discovery\": true
        }
    },
    \"minimum-stability\": \"stable\",
    \"prefer-stable\": true
}
EOF
    fi && \
    echo '   📦 Running composer update...' && \
    composer update --no-dev --optimize-autoloader --no-interaction --prefer-dist 2>&1 | tail -10 && \
    echo '   📦 Regenerating autoloader...' && \
    composer dump-autoload --optimize --no-interaction 2>&1 | tail -5 && \
    echo '   ✅ Composer fix complete'
"
echo ""

# 8. Restart container
echo "8️⃣ Restarting container..."
docker restart scientistcloud-portal
echo "   Waiting 5 seconds for container to start..."
sleep 5
echo ""

# 9. Final test
echo "9️⃣ Final API test..."
sleep 3
FINAL_RESPONSE=$(curl -s https://scientistcloud.com/portal/api/dashboards.php)
if echo "$FINAL_RESPONSE" | python3 -m json.tool >/dev/null 2>&1; then
    echo "   ✅ API is returning valid JSON!"
    echo "$FINAL_RESPONSE" | python3 -m json.tool | head -30
else
    echo "   ❌ API still not working. Response:"
    echo "$FINAL_RESPONSE" | head -50
fi
echo ""

echo "✅ Diagnostic complete!"
echo ""
echo "📋 Summary:"
echo "  - Check the API test results above"
echo "  - If dashboards-list.json is missing, that's the problem"
echo "  - If PHP errors appear, those need to be fixed"
echo "  - If API returns 200 but empty dashboards, check the JSON file format"

