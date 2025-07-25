#!/bin/bash

# 🔒 Fix SQLite Database Lock Issues - OST
# This script diagnoses and fixes database lock problems after large imports

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

echo "🔒 OST Database Lock Fix Tool"
echo "============================="

# Step 1: Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    log_error "Not in Django project directory. Please run from /var/www/ost"
    exit 1
fi

log_info "Step 1: Identifying database lock issues..."

# Find the database file
DB_FILE=$(python manage.py shell -c "
from django.conf import settings
db_config = settings.DATABASES['default']
if 'sqlite' in db_config['ENGINE']:
    print(db_config['NAME'])
else:
    print('Not SQLite')
" 2>/dev/null)

if [ "$DB_FILE" = "Not SQLite" ]; then
    log_error "This script is for SQLite databases only"
    exit 1
fi

log_info "Database file: $DB_FILE"

# Check if database file exists
if [ ! -f "$DB_FILE" ]; then
    log_error "Database file not found: $DB_FILE"
    exit 1
fi

echo ""
log_info "Step 2: Checking for processes locking the database..."

# Find processes that might be locking the database
log_info "Checking for Python processes that might be holding locks..."
PYTHON_PROCS=$(ps aux | grep -E "(python|django|manage\.py|gunicorn)" | grep -v grep | wc -l)
log_info "Found $PYTHON_PROCS Python processes running"

if [ "$PYTHON_PROCS" -gt 0 ]; then
    log_warning "Python processes that might be locking the database:"
    ps aux | grep -E "(python|django|manage\.py|gunicorn)" | grep -v grep
fi

# Check specifically for import processes
log_info "Checking for stuck import processes..."
IMPORT_PROCS=$(ps aux | grep -E "(manual_process|import_.*\.py)" | grep -v grep)
if [ -n "$IMPORT_PROCS" ]; then
    log_error "Found stuck import processes:"
    echo "$IMPORT_PROCS"
    echo ""
    log_info "These processes need to be killed to unlock the database"
fi

echo ""
log_info "Step 3: Checking database lock status..."

# Check for WAL files (Write-Ahead Logging)
if [ -f "${DB_FILE}-wal" ]; then
    WAL_SIZE=$(stat -f%z "${DB_FILE}-wal" 2>/dev/null || stat -c%s "${DB_FILE}-wal" 2>/dev/null || echo "unknown")
    log_warning "WAL file exists: ${DB_FILE}-wal (${WAL_SIZE} bytes)"
    log_info "This indicates potential uncommitted transactions"
fi

if [ -f "${DB_FILE}-shm" ]; then
    log_warning "Shared memory file exists: ${DB_FILE}-shm"
    log_info "This indicates active or interrupted connections"
fi

# Test database accessibility
log_info "Testing database accessibility..."
if timeout 10 sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master;" > /dev/null 2>&1; then
    log_success "Database is accessible"
else
    log_error "Database is locked or corrupted"
fi

echo ""
log_info "Step 4: Stopping all services that might be using the database..."

# Stop Django-related services
log_info "Stopping Gunicorn..."
sudo systemctl stop gunicorn 2>/dev/null || log_warning "Gunicorn service not found or already stopped"

log_info "Stopping any Django development servers..."
pkill -f "manage.py runserver" 2>/dev/null || log_info "No Django dev servers running"

# Kill stuck import processes
log_info "Stopping stuck import processes..."
pkill -f "manual_process.py" 2>/dev/null || log_info "No manual_process.py found"
pkill -f "import_.*\.py" 2>/dev/null || log_info "No import scripts found"

# Wait a moment for processes to stop
sleep 3

echo ""
log_info "Step 5: Attempting to unlock the database..."

# Method 1: Try to unlock using SQLite
log_info "Attempting SQLite unlock..."
if timeout 30 sqlite3 "$DB_FILE" "BEGIN IMMEDIATE; ROLLBACK;" 2>/dev/null; then
    log_success "Database unlocked successfully"
else
    log_warning "SQLite unlock failed, trying alternative methods..."
    
    # Method 2: Remove WAL and SHM files (safe if no active connections)
    if [ -f "${DB_FILE}-wal" ] || [ -f "${DB_FILE}-shm" ]; then
        log_info "Removing WAL and SHM files to force unlock..."
        rm -f "${DB_FILE}-wal" "${DB_FILE}-shm" 2>/dev/null || log_warning "Could not remove WAL/SHM files"
    fi
    
    # Method 3: Database integrity check and repair
    log_info "Running database integrity check..."
    if timeout 30 sqlite3 "$DB_FILE" "PRAGMA integrity_check;" > /tmp/integrity_check.txt 2>&1; then
        if grep -q "ok" /tmp/integrity_check.txt; then
            log_success "Database integrity check passed"
        else
            log_error "Database integrity issues found:"
            cat /tmp/integrity_check.txt
        fi
    else
        log_error "Could not run integrity check - database may be severely corrupted"
    fi
fi

echo ""
log_info "Step 6: Optimizing database after unlock..."

# Database optimization
log_info "Running VACUUM to optimize database..."
if timeout 60 sqlite3 "$DB_FILE" "VACUUM;" 2>/dev/null; then
    log_success "Database VACUUM completed"
else
    log_warning "VACUUM failed - database may still be locked"
fi

log_info "Running ANALYZE to update statistics..."
timeout 30 sqlite3 "$DB_FILE" "ANALYZE;" 2>/dev/null || log_warning "ANALYZE failed"

echo ""
log_info "Step 7: Fixing file permissions..."

# Fix database file permissions
log_info "Fixing database file permissions..."
sudo chown xeradb:www-data "$DB_FILE" 2>/dev/null || sudo chown $USER:$USER "$DB_FILE"
chmod 664 "$DB_FILE"

# Fix directory permissions
DB_DIR=$(dirname "$DB_FILE")
sudo chown xeradb:www-data "$DB_DIR" 2>/dev/null || sudo chown $USER:$USER "$DB_DIR"
chmod 775 "$DB_DIR"

log_success "File permissions fixed"

echo ""
log_info "Step 8: Configuring SQLite for better concurrency..."

# Create optimized SQLite settings
log_info "Applying SQLite optimizations for large datasets..."

# Create a script to apply SQLite optimizations
cat > /tmp/sqlite_optimize.sql << 'EOF'
-- SQLite optimizations for large datasets and concurrency
PRAGMA journal_mode = WAL;          -- Enable Write-Ahead Logging for better concurrency
PRAGMA synchronous = NORMAL;        -- Balance between safety and performance
PRAGMA cache_size = 10000;          -- Increase cache size (10MB)
PRAGMA temp_store = memory;         -- Store temp tables in memory
PRAGMA mmap_size = 268435456;       -- Enable memory mapping (256MB)
PRAGMA page_size = 4096;            -- Optimize page size
PRAGMA auto_vacuum = INCREMENTAL;   -- Enable incremental vacuum
VACUUM;                             -- Clean up database
ANALYZE;                            -- Update query planner statistics
EOF

if timeout 60 sqlite3 "$DB_FILE" < /tmp/sqlite_optimize.sql 2>/dev/null; then
    log_success "SQLite optimizations applied"
else
    log_warning "Some SQLite optimizations failed"
fi

rm -f /tmp/sqlite_optimize.sql

echo ""
log_info "Step 9: Testing database functionality..."

# Test Django database access
cd /var/www/ost
source ost_env/bin/activate

log_info "Testing Django database connection..."
if python manage.py shell -c "
from tracker.models import Paper
try:
    count = Paper.objects.count()
    print(f'✅ Database working: {count:,} papers found')
except Exception as e:
    print(f'❌ Database error: {e}')
    exit(1)
" 2>/dev/null; then
    log_success "Django database connection working"
else
    log_error "Django database connection still failing"
fi

echo ""
log_info "Step 10: Restarting services..."

# Start services back up
log_info "Starting Gunicorn with optimized settings..."

# Create optimized Gunicorn config for database-heavy workloads
sudo tee /etc/systemd/system/gunicorn.service > /dev/null << 'EOF'
[Unit]
Description=Gunicorn instance to serve OST
After=network.target

[Service]
User=xeradb
Group=www-data
WorkingDirectory=/var/www/ost
Environment="PATH=/var/www/ost/ost_env/bin"
ExecStart=/var/www/ost/ost_env/bin/gunicorn --workers 3 --timeout 300 --bind unix:/var/www/ost/ost.sock ost_web.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start gunicorn
sleep 3

if systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn started successfully"
else
    log_error "Gunicorn failed to start"
fi

# Restart Nginx
log_info "Restarting Nginx..."
sudo systemctl restart nginx

if systemctl is-active --quiet nginx; then
    log_success "Nginx restarted successfully"
else
    log_error "Nginx failed to restart"
fi

echo ""
log_info "Step 11: Final verification..."

# Test website
log_info "Testing website accessibility..."
sleep 5

if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|301\|302"; then
    log_success "Website is responding! 502 error should be fixed."
else
    log_warning "Website still not responding. Check logs for details."
fi

echo ""
log_success "Database lock fix completed!"
echo ""
log_info "🔧 Prevention tips for future imports:"
echo "1. Always stop Gunicorn before large imports:"
echo "   sudo systemctl stop gunicorn"
echo ""
echo "2. Use the optimized import with smaller batches:"
echo "   python manage.py import_rtransparent_medical file.csv --batch-size 500"
echo ""
echo "3. Monitor import progress and don't interrupt:"
echo "   python manage.py import_rtransparent_medical file.csv --limit 10000  # Test first"
echo ""
echo "4. Start services after import completes:"
echo "   sudo systemctl start gunicorn"
echo ""
log_info "For monitoring database locks in future:"
echo "   watch -n 5 'sqlite3 $DB_FILE \"SELECT COUNT(*) FROM tracker_paper;\"'"
echo ""
log_info "If database gets locked again, run this script: ./fix_database_lock.sh" 