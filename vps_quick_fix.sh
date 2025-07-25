#!/bin/bash
# Quick VPS Fix for Missing Dependencies and PostgreSQL Lock Issues
# Run this on your VPS to fix the ModuleNotFoundError and database locks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

echo -e "${CYAN}🚨 OST VPS QUICK FIX - Missing Dependencies + PostgreSQL Locks${NC}"
echo "=================================================================="

# Step 1: Install missing dependencies
log_info "Step 1: Installing missing Python dependencies..."
cd /var/www/ost
source ost_env/bin/activate

pip install -r requirements.txt
log_success "Dependencies installed!"

# Step 2: Run the PostgreSQL lock fix
log_info "Step 2: Running PostgreSQL lock fix..."
chmod +x fix_postgres_lock.sh
./fix_postgres_lock.sh

# Step 3: Restart services
log_info "Step 3: Restarting web services..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Step 4: Health check
log_info "Step 4: Performing health check..."
sleep 5

if curl -f http://localhost/ > /dev/null 2>&1; then
    log_success "✨ Website is responding! Fix successful!"
    log_info "🎯 Database: ost_production"
    log_info "🚀 All services are running"
else
    log_warning "Website not responding yet. Check service status:"
    echo "  sudo systemctl status gunicorn"
    echo "  sudo systemctl status nginx"
    echo "  sudo journalctl -u gunicorn -f"
fi

echo ""
echo -e "${GREEN}🎉 Quick fix completed!${NC}"
echo "Your OST website should now be accessible." 