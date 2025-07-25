#!/bin/bash

# 🚨 Fix 502 Bad Gateway Error After Large Database Import
# This script diagnoses and fixes common issues after importing large datasets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🚨 OST 502 Bad Gateway Fix - Post Large Import"
echo "=============================================="

# Step 1: Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    log_error "Not in Django project directory. Please run from /var/www/ost"
    exit 1
fi

log_info "Step 1: Checking service status..."

# Check Gunicorn status
log_info "Checking Gunicorn service..."
if systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn is running"
else
    log_error "Gunicorn is not running - this is likely the cause!"
fi

# Check Nginx status
log_info "Checking Nginx service..."
if systemctl is-active --quiet nginx; then
    log_success "Nginx is running"
else
    log_warning "Nginx is not running"
fi

echo ""
log_info "Step 2: Checking system resources..."

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
log_info "Memory usage: ${MEMORY_USAGE}%"

if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    log_error "High memory usage detected! This may have caused Gunicorn to crash."
fi

# Check disk space
DISK_USAGE=$(df /var/www/ost | awk 'NR==2 {print $5}' | sed 's/%//')
log_info "Disk usage: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 90 ]; then
    log_error "Low disk space detected!"
fi

echo ""
log_info "Step 3: Checking database..."

# Check database size
cd /var/www/ost
source ost_env/bin/activate

# Check if database is accessible
log_info "Testing database connectivity..."
if python manage.py shell -c "from tracker.models import Paper; print(f'Papers in DB: {Paper.objects.count():,}')" 2>/dev/null; then
    log_success "Database is accessible"
else
    log_error "Database connection issues detected"
fi

echo ""
log_info "Step 4: Checking application logs..."

# Check Gunicorn logs
if [ -f "/var/log/gunicorn/error.log" ]; then
    log_info "Recent Gunicorn errors:"
    tail -20 /var/log/gunicorn/error.log | grep -E "(ERROR|CRITICAL|MemoryError|killed)" || log_info "No critical errors in recent logs"
fi

# Check system logs for OOM killer
log_info "Checking for Out of Memory kills..."
if dmesg | grep -E "(killed|oom-killer)" | tail -5; then
    log_error "Out of Memory killer detected - Gunicorn was likely killed due to memory exhaustion"
else
    log_info "No OOM kills detected"
fi

echo ""
log_info "Step 5: Applying fixes..."

# Fix 1: Restart services
log_info "Restarting Gunicorn..."
sudo systemctl stop gunicorn
sleep 2
sudo systemctl start gunicorn
sleep 3

if systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn restarted successfully"
else
    log_error "Gunicorn failed to start. Trying with optimized settings..."
    
    # Create optimized Gunicorn config for large datasets
    log_info "Creating optimized Gunicorn configuration..."
    
    cat > /tmp/gunicorn_optimized.py << 'EOF'
# Optimized Gunicorn config for large datasets
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = min(4, multiprocessing.cpu_count())
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased timeout for large queries
keepalive = 2

# Memory management
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 50
preload_app = True

# Logging
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
accesslog = "/var/log/gunicorn/access.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "ost_gunicorn"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
EOF

    # Copy optimized config
    sudo cp /tmp/gunicorn_optimized.py /etc/gunicorn/ost_config.py
    
    # Restart with optimized config
    sudo systemctl restart gunicorn
    sleep 5
    
    if systemctl is-active --quiet gunicorn; then
        log_success "Gunicorn started with optimized configuration"
    else
        log_error "Gunicorn still failing. Manual intervention required."
    fi
fi

# Fix 2: Restart Nginx
log_info "Restarting Nginx..."
sudo systemctl restart nginx

if systemctl is-active --quiet nginx; then
    log_success "Nginx restarted successfully"
else
    log_error "Nginx failed to restart"
fi

echo ""
log_info "Step 6: Testing website..."

# Test local connection
log_info "Testing local Django application..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|301\|302"; then
    log_success "Django application responding locally"
else
    log_error "Django application not responding locally"
fi

# Test through Nginx
log_info "Testing through Nginx..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|301\|302"; then
    log_success "Website responding through Nginx"
else
    log_warning "Website still not responding through Nginx"
fi

echo ""
log_info "Step 7: Performance optimization for large dataset..."

# Run database optimization
log_info "Running database optimization..."
cd /var/www/ost
source ost_env/bin/activate

# Optimize database
python manage.py performance_optimize --action=optimize 2>/dev/null || log_warning "Performance optimization failed"

# Warm cache to reduce initial load
log_info "Warming cache to improve performance..."
python manage.py performance_optimize --action=warm-cache 2>/dev/null || log_warning "Cache warming failed"

echo ""
log_info "Step 8: Memory optimization recommendations..."

# Check current paper count
PAPER_COUNT=$(python manage.py shell -c "from tracker.models import Paper; print(Paper.objects.count())" 2>/dev/null || echo "unknown")
log_info "Current papers in database: ${PAPER_COUNT}"

if [ "$PAPER_COUNT" != "unknown" ] && [ "$PAPER_COUNT" -gt 1000000 ]; then
    log_warning "Large dataset detected (${PAPER_COUNT} papers). Consider these optimizations:"
    echo "   • Increase server memory (recommended: 4GB+ for 1M+ papers)"
    echo "   • Enable Redis caching for better performance"
    echo "   • Consider database connection pooling"
    echo "   • Implement pagination limits"
fi

echo ""
log_success "502 Fix script completed!"
echo ""
echo "🔍 Next steps if still having issues:"
echo "1. Check logs: sudo journalctl -u gunicorn -f"
echo "2. Monitor memory: watch -n 1 'free -h'"
echo "3. Check Django debug: python manage.py runserver (temporarily)"
echo "4. Contact support with log details"

echo ""
log_info "For real-time monitoring, run:"
echo "   python manage.py performance_optimize --action=monitor" 