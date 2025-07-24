#!/bin/bash

# ==============================================================================
# OST Logging Permission Fix Script
# ==============================================================================
# Fixes logging permission issues after GitHub pulls
# Run this on your VPS when manual_process.py fails with permission errors
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 OST Logging Permission Fix${NC}"
echo "=================================="

# Set project directory
PROJECT_DIR="/var/www/ost"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory $PROJECT_DIR not found!${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Create log directories
echo -e "${YELLOW}📁 Creating log directories...${NC}"
sudo mkdir -p /var/log/ost
mkdir -p logs

# Set ownership
echo -e "${YELLOW}👤 Setting ownership...${NC}"
sudo chown -R $USER:www-data /var/log/ost 2>/dev/null || true
sudo chown -R $USER:www-data "$PROJECT_DIR/logs" 2>/dev/null || true
sudo chown -R $USER:www-data "$PROJECT_DIR" 2>/dev/null || true

# Set permissions
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
sudo chmod -R 775 /var/log/ost 2>/dev/null || true
chmod -R 775 logs 2>/dev/null || true
chmod -R 755 . 2>/dev/null || true

# Create log files
echo -e "${YELLOW}📝 Creating log files...${NC}"
sudo touch /var/log/ost/ost.log 2>/dev/null || true
touch logs/ost.log 2>/dev/null || true
sudo chown $USER:www-data /var/log/ost/ost.log 2>/dev/null || true
chown $USER:www-data logs/ost.log 2>/dev/null || true
sudo chmod 664 /var/log/ost/ost.log 2>/dev/null || true
chmod 664 logs/ost.log 2>/dev/null || true

# Test Django startup
echo -e "${YELLOW}🧪 Testing Django configuration...${NC}"
if [ -f "ost_env/bin/activate" ]; then
    source ost_env/bin/activate
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
try:
    django.setup()
    print('✅ Django configuration successful!')
except Exception as e:
    print(f'❌ Django setup failed: {e}')
    exit(1)
" || {
        echo -e "${RED}❌ Django configuration test failed${NC}"
        exit 1
    }
else
    echo -e "${YELLOW}⚠️ Virtual environment not found, skipping Django test${NC}"
fi

echo ""
echo -e "${GREEN}✅ Logging permissions fixed!${NC}"
echo -e "${BLUE}📍 Log files available at:${NC}"
echo "   - /var/log/ost/ost.log (primary)"
echo "   - $PROJECT_DIR/logs/ost.log (backup)"
echo ""
echo -e "${GREEN}🚀 Ready to run manual_process.py!${NC}"
echo ""
echo -e "${BLUE}💡 To test:${NC}"
echo "   python scripts/manual_process.py --test"
echo "   python scripts/manual_process.py --all" 