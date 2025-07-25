#!/bin/bash

# ==============================================================================
# OST Deployment Diagnosis Script
# ==============================================================================
# Diagnoses why VPS site doesn't match local version after deployment
# Run this on your VPS to identify and fix common deployment issues
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

echo -e "${BLUE}🔍 OST Deployment Diagnosis${NC}"
echo "============================="

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory $PROJECT_DIR not found!${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${CYAN}📋 SYSTEM INFORMATION${NC}"
echo "----------------------------------------"
echo "Current directory: $(pwd)"
echo "Current user: $(whoami)"
echo "Current time: $(date)"
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'Unknown')"
echo ""

echo -e "${CYAN}🔍 DJANGO CONFIGURATION CHECK${NC}"
echo "----------------------------------------"
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    
    # Check Django settings
    echo "Testing Django configuration..."
    $PYTHON_BIN -c "
import os
import django
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from django.conf import settings
print(f'DEBUG: {settings.DEBUG}')
print(f'STATIC_URL: {settings.STATIC_URL}')
print(f'STATIC_ROOT: {settings.STATIC_ROOT}')
print(f'STATICFILES_DIRS: {settings.STATICFILES_DIRS}')

# Check if static root exists
static_root = Path(settings.STATIC_ROOT)
print(f'STATIC_ROOT exists: {static_root.exists()}')
if static_root.exists():
    print(f'STATIC_ROOT permissions: {oct(static_root.stat().st_mode)[-3:]}')
    
# Check for dark theme CSS
dark_theme_path = static_root / 'css' / 'dark-theme.css'
print(f'Dark theme CSS exists: {dark_theme_path.exists()}')
if dark_theme_path.exists():
    size = dark_theme_path.stat().st_size
    print(f'Dark theme CSS size: {size} bytes')
    modified = dark_theme_path.stat().st_mtime
    import datetime
    print(f'Dark theme CSS modified: {datetime.datetime.fromtimestamp(modified)}')
"
    deactivate
else
    echo -e "${RED}❌ Virtual environment not found!${NC}"
fi

echo ""
echo -e "${CYAN}📁 STATIC FILES CHECK${NC}"
echo "----------------------------------------"

# Check staticfiles directory
if [ -d "staticfiles" ]; then
    echo "✅ staticfiles directory exists"
    echo "Permission: $(ls -ld staticfiles | awk '{print $1}')"
    echo "Owner: $(ls -ld staticfiles | awk '{print $3":"$4}')"
    echo "Files count: $(find staticfiles -type f | wc -l)"
    
    # Check specific files
    if [ -f "staticfiles/css/dark-theme.css" ]; then
        echo "✅ dark-theme.css found in staticfiles"
        echo "   Size: $(wc -c < staticfiles/css/dark-theme.css) bytes"
        echo "   Modified: $(date -r staticfiles/css/dark-theme.css)"
    else
        echo "❌ dark-theme.css NOT found in staticfiles"
    fi
    
    if [ -f "staticfiles/css/xera-unified-theme.css" ]; then
        echo "✅ xera-unified-theme.css found in staticfiles"
    else
        echo "❌ xera-unified-theme.css NOT found in staticfiles"
    fi
else
    echo -e "${RED}❌ staticfiles directory does not exist!${NC}"
fi

# Check source static files
echo ""
echo "Source static files:"
if [ -d "static" ]; then
    echo "✅ static directory exists"
    if [ -f "static/css/dark-theme.css" ]; then
        echo "✅ dark-theme.css found in source static"
        echo "   Size: $(wc -c < static/css/dark-theme.css) bytes"
        echo "   Modified: $(date -r static/css/dark-theme.css)"
    else
        echo "❌ dark-theme.css NOT found in source static"
    fi
else
    echo -e "${RED}❌ static directory does not exist!${NC}"
fi

echo ""
echo -e "${CYAN}🌐 NGINX CONFIGURATION CHECK${NC}"
echo "----------------------------------------"

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    echo -e "${RED}❌ Nginx is not running!${NC}"
fi

# Check Nginx configuration
if [ -f "/etc/nginx/sites-available/ost" ]; then
    echo "✅ Nginx configuration exists"
    echo "Static files configuration:"
    grep -A 5 -B 2 "location /static" /etc/nginx/sites-available/ost || echo "No static location block found"
elif [ -f "/etc/nginx/sites-enabled/ost" ]; then
    echo "✅ Nginx configuration exists (enabled)"
    echo "Static files configuration:"
    grep -A 5 -B 2 "location /static" /etc/nginx/sites-enabled/ost || echo "No static location block found"
else
    echo -e "${YELLOW}⚠️ OST Nginx configuration not found in standard locations${NC}"
fi

# Test Nginx configuration
echo "Testing Nginx configuration:"
sudo nginx -t 2>&1 | head -5

echo ""
echo -e "${CYAN}🔧 SERVICE STATUS CHECK${NC}"
echo "----------------------------------------"

# Check common service names
for service in "ost-gunicorn" "gunicorn" "ost" "django"; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "✅ $service is running"
        echo "   Status: $(systemctl show -p SubState --value $service)"
        echo "   Since: $(systemctl show -p ActiveEnterTimestamp --value $service)"
    fi
done

# Check for supervisor
if command -v supervisorctl >/dev/null 2>&1; then
    echo ""
    echo "Supervisor status:"
    sudo supervisorctl status | grep -i ost || echo "No OST processes in supervisor"
fi

echo ""
echo -e "${CYAN}🌐 CONNECTIVITY TEST${NC}"
echo "----------------------------------------"

# Test local connectivity
echo "Testing local HTTP connectivity:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "✅ Local HTTP (port 80) working"
else
    echo "❌ Local HTTP (port 80) not responding"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
    echo "✅ Django dev server (port 8000) working"
else
    echo "❌ Django dev server (port 8000) not responding"
fi

# Test static file access
echo ""
echo "Testing static file access:"
for url in "http://localhost/static/css/dark-theme.css" "http://localhost/static/css/xera-unified-theme.css"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$status" = "200" ]; then
        echo "✅ $url accessible (HTTP $status)"
    else
        echo "❌ $url not accessible (HTTP $status)"
    fi
done

echo ""
echo -e "${CYAN}🔍 RECENT CHANGES CHECK${NC}"
echo "----------------------------------------"

# Check git status
echo "Git status:"
git status --porcelain | head -10 || echo "No git changes"

# Check recent commits
echo ""
echo "Recent commits:"
git log --oneline -5 || echo "No git history"

echo ""
echo -e "${CYAN}💡 RECOMMENDED ACTIONS${NC}"
echo "----------------------------------------"

# Provide recommendations based on findings
echo "1. 🔄 Force static files collection:"
echo "   cd $PROJECT_DIR && source ost_env/bin/activate"
echo "   python manage.py collectstatic --noinput --clear"
echo ""

echo "2. 🔧 Fix static files permissions:"
echo "   sudo chown -R www-data:www-data staticfiles/"
echo "   sudo chmod -R 644 staticfiles/"
echo ""

echo "3. 🔄 Restart all services:"
echo "   sudo systemctl restart nginx"
echo "   sudo systemctl restart ost-gunicorn  # or your Django service"
echo ""

echo "4. 🧹 Clear browser cache:"
echo "   - Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)"
echo "   - Or open in incognito/private browsing mode"
echo ""

echo "5. 📡 Test direct static file URLs:"
echo "   curl -I http://your-domain.com/static/css/dark-theme.css"
echo ""

echo -e "${GREEN}🏁 Diagnosis complete!${NC}"
echo "Run the recommended actions above to fix any issues found." 