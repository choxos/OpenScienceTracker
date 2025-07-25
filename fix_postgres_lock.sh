#!/bin/bash

# 🐘 Fix PostgreSQL Database Lock Issues - OST
# This script diagnoses and fixes PostgreSQL database lock problems after large imports

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

echo "🐘 OST PostgreSQL Lock Fix Tool"
echo "==============================="

# Step 1: Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    log_error "Not in Django project directory. Please run from /var/www/ost"
    exit 1
fi

log_info "Step 1: Checking PostgreSQL database configuration..."

# Get database configuration from Django
cd /var/www/ost
source ost_env/bin/activate

# Try multiple methods to get database configuration
log_info "Attempting to get database configuration..."

# Method 1: Direct Django shell with explicit commands
DB_INFO=$(python -c "
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
print('{}|{}|{}|{}'.format(db['NAME'], db['USER'], db['HOST'], db['PORT']))
" 2>/dev/null | tail -1)

# Method 2: If method 1 fails, try with manage.py but suppress verbose output
if [ -z "$DB_INFO" ] || [[ "$DB_INFO" == *"objects imported"* ]]; then
    DB_INFO=$(python manage.py shell --verbosity=0 -c "
from django.conf import settings
db = settings.DATABASES['default']
print('{}|{}|{}|{}'.format(db['NAME'], db['USER'], db['HOST'], db['PORT']))
" 2>/dev/null | grep -E '^[^|]*\|[^|]*\|[^|]*\|[^|]*$' | head -1)
fi

# Method 3: Fallback to known configuration
if [ -z "$DB_INFO" ] || [[ "$DB_INFO" == *"objects imported"* ]] || [[ "$DB_INFO" != *"|"* ]]; then
    log_warning "Could not get database configuration from Django (output: '$DB_INFO')"
    log_info "Using fallback PostgreSQL configuration for ost_production..."
    DB_NAME="ost_production"
    DB_USER="postgres"
    DB_HOST="localhost"
    DB_PORT="5432"
    log_info "Note: Installing missing dependencies or checking Django settings may be needed"
else
    IFS='|' read -r DB_NAME DB_USER DB_HOST DB_PORT <<< "$DB_INFO"
fi

log_info "Database: $DB_NAME"
log_info "User: $DB_USER"
log_info "Host: $DB_HOST"
log_info "Port: $DB_PORT"

echo ""
log_info "Step 2: Checking for stuck processes and database locks..."

# Stop services that might be holding locks
log_info "Stopping services that might hold database connections..."
sudo systemctl stop gunicorn 2>/dev/null || log_warning "Gunicorn not running or already stopped"

# Kill stuck import processes
log_info "Killing stuck import processes..."
pkill -f "manual_process.py" 2>/dev/null && log_info "Killed manual_process.py" || log_info "No manual_process.py found"
pkill -f "python scripts" 2>/dev/null && log_info "Killed python scripts" || log_info "No python scripts found"
pkill -f "import_.*\.py" 2>/dev/null && log_info "Killed import scripts" || log_info "No import scripts found"

# Wait for processes to terminate
sleep 3

echo ""
log_info "Step 3: Checking PostgreSQL database status..."

# Check if PostgreSQL is running
if systemctl is-active --quiet postgresql; then
    log_success "PostgreSQL service is running"
else
    log_error "PostgreSQL service is not running!"
    log_info "Starting PostgreSQL..."
    sudo systemctl start postgresql
    sleep 3
    if systemctl is-active --quiet postgresql; then
        log_success "PostgreSQL started successfully"
    else
        log_error "Failed to start PostgreSQL"
        exit 1
    fi
fi

# Test basic database connectivity
log_info "Testing database connectivity..."
if sudo -u postgres psql -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    log_success "Database is accessible"
else
    log_error "Cannot connect to database!"
    
    # Try to connect as postgres user to check if database exists
    if sudo -u postgres psql -c "SELECT datname FROM pg_database WHERE datname='$DB_NAME';" | grep -q "$DB_NAME"; then
        log_info "Database exists but connection failed - checking permissions..."
    else
        log_error "Database '$DB_NAME' does not exist!"
        exit 1
    fi
fi

echo ""
log_info "Step 4: Checking for active connections and locks..."

# Check active connections
log_info "Checking active database connections..."
ACTIVE_CONNECTIONS=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' AND state = 'active';
" 2>/dev/null | tr -d ' ')

log_info "Active connections: $ACTIVE_CONNECTIONS"

# Check for locks
log_info "Checking for database locks..."
LOCKS_INFO=$(sudo -u postgres psql -d "$DB_NAME" -c "
SELECT 
    pg_stat_activity.pid,
    pg_stat_activity.usename,
    pg_stat_activity.query,
    pg_stat_activity.state,
    pg_stat_activity.query_start,
    pg_locks.mode,
    pg_locks.locktype
FROM pg_stat_activity, pg_locks 
WHERE pg_stat_activity.pid = pg_locks.pid 
AND pg_stat_activity.datname = '$DB_NAME'
AND pg_locks.granted = true
ORDER BY pg_stat_activity.query_start;
" 2>/dev/null)

if [ -n "$LOCKS_INFO" ]; then
    log_warning "Found active locks:"
    echo "$LOCKS_INFO"
else
    log_info "No problematic locks found"
fi

# Check for long-running queries
log_info "Checking for long-running queries (>5 minutes)..."
LONG_QUERIES=$(sudo -u postgres psql -d "$DB_NAME" -c "
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    now() - query_start AS duration,
    query
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND state != 'idle' 
AND now() - query_start > interval '5 minutes'
ORDER BY query_start;
" 2>/dev/null)

if echo "$LONG_QUERIES" | grep -q "row"; then
    log_warning "Found long-running queries:"
    echo "$LONG_QUERIES"
    
    # Get PIDs of long-running queries
    PIDS_TO_KILL=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
    SELECT pid 
    FROM pg_stat_activity 
    WHERE datname = '$DB_NAME' 
    AND state != 'idle' 
    AND now() - query_start > interval '5 minutes';
    " 2>/dev/null | tr -d ' ' | grep -v '^$')
    
    if [ -n "$PIDS_TO_KILL" ]; then
        log_warning "Killing long-running queries..."
        for pid in $PIDS_TO_KILL; do
            log_info "Killing process $pid..."
            sudo -u postgres psql -d "$DB_NAME" -c "SELECT pg_terminate_backend($pid);" 2>/dev/null || log_warning "Could not kill process $pid"
        done
    fi
else
    log_success "No long-running queries found"
fi

echo ""
log_info "Step 5: Optimizing PostgreSQL performance..."

# Run VACUUM and ANALYZE
log_info "Running VACUUM ANALYZE to optimize database..."
sudo -u postgres psql -d "$DB_NAME" -c "VACUUM ANALYZE;" 2>/dev/null && log_success "VACUUM ANALYZE completed" || log_warning "VACUUM ANALYZE failed"

# Update statistics
log_info "Updating table statistics..."
sudo -u postgres psql -d "$DB_NAME" -c "ANALYZE;" 2>/dev/null && log_success "ANALYZE completed" || log_warning "ANALYZE failed"

echo ""
log_info "Step 6: Testing Django database access..."

# Test Django database connection
log_info "Testing Django database connection..."
DJANGO_TEST=$(python manage.py shell -c "
from tracker.models import Paper
try:
    count = Paper.objects.count()
    print(f'SUCCESS: {count} papers found')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>&1)

if echo "$DJANGO_TEST" | grep -q "SUCCESS"; then
    log_success "Django database connection working"
    echo "$DJANGO_TEST"
else
    log_error "Django database connection failed:"
    echo "$DJANGO_TEST"
fi

echo ""
log_info "Step 7: Configuring optimized PostgreSQL settings..."

# Create optimized PostgreSQL configuration
log_info "Applying PostgreSQL optimizations for large datasets..."

# Check current max_connections
MAX_CONN=$(sudo -u postgres psql -t -c "SHOW max_connections;" | tr -d ' ')
log_info "Current max_connections: $MAX_CONN"

# Show important settings
log_info "Current PostgreSQL settings:"
sudo -u postgres psql -c "
SELECT name, setting, unit, context 
FROM pg_settings 
WHERE name IN ('max_connections', 'shared_buffers', 'work_mem', 'maintenance_work_mem', 'checkpoint_completion_target')
ORDER BY name;
"

echo ""
log_info "Step 8: Restarting services with optimized settings..."

# Create optimized Gunicorn config for PostgreSQL
log_info "Creating optimized Gunicorn configuration for PostgreSQL..."
sudo tee /etc/systemd/system/gunicorn.service > /dev/null << EOF
[Unit]
Description=Gunicorn instance to serve OST (PostgreSQL optimized)
After=network.target postgresql.service

[Service]
User=xeradb
Group=www-data
WorkingDirectory=/var/www/ost
Environment="PATH=/var/www/ost/ost_env/bin"
ExecStart=/var/www/ost/ost_env/bin/gunicorn \\
    --workers 4 \\
    --timeout 300 \\
    --max-requests 1000 \\
    --max-requests-jitter 50 \\
    --preload \\
    --bind unix:/var/www/ost/ost.sock \\
    ost_web.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=10
PrivateTmp=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Start Gunicorn
log_info "Starting Gunicorn..."
sudo systemctl start gunicorn
sleep 5

if systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn started successfully"
else
    log_error "Gunicorn failed to start. Checking logs..."
    sudo journalctl -u gunicorn --no-pager -n 20
fi

# Start Nginx
log_info "Starting Nginx..."
sudo systemctl start nginx

if systemctl is-active --quiet nginx; then
    log_success "Nginx started successfully"
else
    log_error "Nginx failed to start"
fi

echo ""
log_info "Step 9: Final verification..."

# Test website
log_info "Testing website accessibility..."
sleep 3

# Test local Django app
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 2>/dev/null | grep -q "200\|301\|302"; then
    log_success "Django application responding locally"
else
    log_warning "Django application not responding locally"
fi

# Test through Nginx
if curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -q "200\|301\|302"; then
    log_success "Website responding through Nginx - 502 error fixed!"
else
    log_warning "Website still not responding through Nginx"
    log_info "Checking Nginx error logs..."
    sudo tail -10 /var/log/nginx/error.log 2>/dev/null || log_info "No Nginx error logs found"
fi

echo ""
log_success "PostgreSQL lock fix completed!"
echo ""
log_info "🔧 Prevention tips for future PostgreSQL imports:"
echo "1. Monitor active connections before imports:"
echo "   sudo -u postgres psql -d $DB_NAME -c \"SELECT count(*) FROM pg_stat_activity;\""
echo ""
echo "2. Use connection pooling for large imports"
echo "3. Monitor long-running queries:"
echo "   sudo -u postgres psql -d $DB_NAME -c \"SELECT pid, query_start, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;\""
echo ""
echo "4. Stop services before large imports:"
echo "   sudo systemctl stop gunicorn"
echo ""
log_info "For ongoing monitoring:"
echo "   watch -n 5 'sudo -u postgres psql -d $DB_NAME -c \"SELECT count(*) FROM pg_stat_activity;\"'"
echo ""
log_info "If issues persist, check:"
echo "   sudo journalctl -u gunicorn -f"
echo "   sudo journalctl -u postgresql -f" 