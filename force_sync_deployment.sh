#!/bin/bash

# ==============================================================================
# OST Force Sync Deployment Script
# ==============================================================================
# Forces VPS to exactly match local version
# Use when deploy.sh doesn't fully sync changes
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/ost"
VENV_DIR="$PROJECT_DIR/ost_env"
PYTHON_BIN="$VENV_DIR/bin/python"

echo -e "${BLUE}🔄 OST Force Sync Deployment${NC}"
echo "=============================="

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory $PROJECT_DIR not found!${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${CYAN}1️⃣ GIT CLEANUP & PULL${NC}"
echo "----------------------------------------"

# Reset any local changes and pull latest
echo "🔧 Cleaning up Git state..."
git status
git reset --hard HEAD
git clean -fd
git pull origin main
echo "✅ Latest code pulled"

echo ""
echo -e "${CYAN}2️⃣ PYTHON ENVIRONMENT${NC}"
echo "----------------------------------------"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip and reinstall requirements
echo "🐍 Updating Python packages..."
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -r requirements.txt --upgrade --force-reinstall
echo "✅ Python packages updated"

echo ""
echo -e "${CYAN}3️⃣ STATIC FILES NUCLEAR RESET${NC}"
echo "----------------------------------------"

# Remove all collected static files
echo "🧹 Clearing existing static files..."
if [ -d "staticfiles" ]; then
    rm -rf staticfiles/*
    echo "✅ Existing static files cleared"
fi

# Force collect static files
echo "📦 Collecting static files (with clear)..."
$PYTHON_BIN manage.py collectstatic --noinput --clear --verbosity=2
echo "✅ Static files collected"

# Fix permissions
echo "🔐 Setting static files permissions..."
sudo chown -R www-data:www-data staticfiles/ 2>/dev/null || chown -R $USER:www-data staticfiles/
sudo chmod -R 644 staticfiles/
sudo find staticfiles/ -type d -exec chmod 755 {} \;
echo "✅ Static files permissions fixed"

echo ""
echo -e "${CYAN}4️⃣ DATABASE OPERATIONS${NC}"
echo "----------------------------------------"

# Run migrations
echo "🗄️ Running database migrations..."
$PYTHON_BIN manage.py migrate --verbosity=2
echo "✅ Migrations completed"

# Clear Django cache
echo "🧹 Clearing Django cache..."
$PYTHON_BIN manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared successfully')
" 2>/dev/null || echo "Cache clearing skipped (not configured)"

echo ""
echo -e "${CYAN}5️⃣ VERIFICATION CHECKS${NC}"
echo "----------------------------------------"

# Verify key files exist
echo "🔍 Verifying critical files..."

files_to_check=(
    "staticfiles/css/dark-theme.css"
    "staticfiles/css/xera-unified-theme.css"
    "staticfiles/css/transparency-colors.css"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        echo "✅ $file exists (${size} bytes)"
    else
        echo -e "${RED}❌ $file missing!${NC}"
    fi
done

# Check Django configuration
echo ""
echo "🧪 Testing Django configuration..."
$PYTHON_BIN -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from django.conf import settings
print(f'✅ Django setup successful')
print(f'DEBUG: {settings.DEBUG}')
print(f'STATIC_ROOT: {settings.STATIC_ROOT}')

# Test dark theme CSS specifically
from pathlib import Path
dark_theme = Path(settings.STATIC_ROOT) / 'css' / 'dark-theme.css'
if dark_theme.exists():
    size = dark_theme.stat().st_size
    print(f'✅ Dark theme CSS: {size} bytes')
    if size > 10000:  # Should be substantial file
        print('✅ Dark theme CSS size looks good')
    else:
        print('⚠️ Dark theme CSS seems small')
else:
    print('❌ Dark theme CSS not found in STATIC_ROOT')
"

deactivate

echo ""
echo -e "${CYAN}6️⃣ SERVICE RESTART${NC}"
echo "----------------------------------------"

# Stop services
echo "🛑 Stopping services..."

# Try different service names
for service in "ost-gunicorn" "gunicorn" "ost" "django"; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "Stopping $service..."
        sudo systemctl stop "$service"
    fi
done

# Check supervisor
if command -v supervisorctl >/dev/null 2>&1; then
    echo "Stopping supervisor processes..."
    sudo supervisorctl stop all 2>/dev/null || true
fi

# Wait for processes to stop
sleep 3

# Restart Nginx first
echo "🔄 Restarting Nginx..."
sudo systemctl restart nginx
sleep 2

# Start application services
echo "🚀 Starting application services..."

# Try to start common service names
for service in "ost-gunicorn" "gunicorn" "ost" "django"; do
    if systemctl list-unit-files | grep -q "^$service.service"; then
        echo "Starting $service..."
        sudo systemctl start "$service"
        sleep 2
        if systemctl is-active --quiet "$service"; then
            echo "✅ $service started successfully"
        else
            echo -e "${YELLOW}⚠️ $service failed to start${NC}"
        fi
    fi
done

# Start supervisor if available
if command -v supervisorctl >/dev/null 2>&1; then
    echo "Starting supervisor processes..."
    sudo supervisorctl start all 2>/dev/null || true
fi

echo ""
echo -e "${CYAN}7️⃣ CONNECTIVITY TESTS${NC}"
echo "----------------------------------------"

# Wait for services to fully start
echo "⏳ Waiting for services to start..."
sleep 5

# Test local connectivity
echo "🌐 Testing connectivity..."

# Test localhost
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "✅ Local HTTP working"
else
    echo -e "${RED}❌ Local HTTP not responding${NC}"
fi

# Test static files directly
echo ""
echo "📦 Testing static file access..."
static_urls=(
    "http://localhost/static/css/dark-theme.css"
    "http://localhost/static/css/xera-unified-theme.css"
)

for url in "${static_urls[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$response" = "200" ]; then
        echo "✅ $url (HTTP $response)"
    else
        echo -e "${RED}❌ $url (HTTP $response)${NC}"
    fi
done

echo ""
echo -e "${CYAN}8️⃣ FINAL VERIFICATION${NC}"
echo "----------------------------------------"

# Get file hashes for verification
echo "🔍 File verification hashes:"
if [ -f "staticfiles/css/dark-theme.css" ]; then
    hash=$(md5sum "staticfiles/css/dark-theme.css" | cut -d' ' -f1)
    echo "Dark theme CSS: $hash"
fi

if [ -f "static/css/dark-theme.css" ]; then
    source_hash=$(md5sum "static/css/dark-theme.css" | cut -d' ' -f1)
    echo "Source dark theme: $source_hash"
    
    if [ "$hash" = "$source_hash" ]; then
        echo "✅ Static files match source files"
    else
        echo -e "${YELLOW}⚠️ Static files don't match source (re-run collectstatic?)${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 FORCE SYNC COMPLETE!${NC}"
echo "======================================="
echo ""
echo -e "${BLUE}💡 NEXT STEPS:${NC}"
echo "1. Test your website in browser"
echo "2. Try hard refresh (Ctrl+F5 or Cmd+Shift+R)"
echo "3. Test dark theme toggle"
echo "4. Check different pages (fields, papers, statistics)"
echo ""
echo -e "${YELLOW}🧹 If still not working:${NC}"
echo "1. Clear browser cache completely"
echo "2. Try incognito/private browsing"
echo "3. Check browser developer tools for CSS 404 errors"
echo "4. Run: curl -I http://your-domain.com/static/css/dark-theme.css"
echo ""
echo -e "${GREEN}✅ VPS should now match your local version!${NC}" 