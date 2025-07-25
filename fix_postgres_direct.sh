#!/bin/bash
# Direct PostgreSQL Lock Fix for OST Production Database
# Uses known database configuration to avoid Django detection issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_header() { echo -e "${PURPLE}🐘 $1${NC}"; }

log_header "OST PostgreSQL Direct Fix Tool"
echo "================================="

# Use known database configuration
DB_NAME="ost_production"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

log_info "Using known database configuration:"
log_info "Database: $DB_NAME"
log_info "User: $DB_USER"
log_info "Host: $DB_HOST"
log_info "Port: $DB_PORT"

echo ""
log_info "Step 1: Stopping services that might hold database connections..."

# Stop services that might be holding locks
sudo systemctl stop gunicorn 2>/dev/null && log_success "Stopped Gunicorn" || log_warning "Gunicorn not running"
sudo systemctl stop nginx 2>/dev/null && log_success "Stopped Nginx" || log_warning "Nginx not running"

# Kill stuck import processes
log_info "Killing stuck import processes..."
pkill -f "manual_process.py" 2>/dev/null && log_success "Killed manual_process.py" || log_info "No manual_process.py found"
pkill -f "python.*import" 2>/dev/null && log_success "Killed import scripts" || log_info "No import scripts found"
pkill -f "gunicorn" 2>/dev/null && log_success "Killed remaining gunicorn processes" || log_info "No gunicorn processes found"

# Wait for processes to terminate
sleep 3

echo ""
log_info "Step 2: Checking PostgreSQL service status..."

if sudo systemctl is-active --quiet postgresql; then
    log_success "PostgreSQL service is running"
else
    log_warning "PostgreSQL service not running, starting it..."
    sudo systemctl start postgresql
    sleep 2
    if sudo systemctl is-active --quiet postgresql; then
        log_success "PostgreSQL started successfully"
    else
        log_error "Failed to start PostgreSQL"
        exit 1
    fi
fi

echo ""
log_info "Step 3: Checking database connectivity..."

if sudo -u postgres psql -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    log_success "Database connection successful"
else
    log_error "Cannot connect to database '$DB_NAME'"
    log_info "Available databases:"
    sudo -u postgres psql -l | grep -E "^\s*\w+" || log_warning "Could not list databases"
    exit 1
fi

echo ""
log_info "Step 4: Checking for active database connections and locks..."

# Show current connections
ACTIVE_CONNECTIONS=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' AND state != 'idle';" 2>/dev/null | xargs)

log_info "Active connections to $DB_NAME: $ACTIVE_CONNECTIONS"

# Show long-running queries
LONG_QUERIES=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND state != 'idle' 
AND now() - query_start > interval '5 minutes';" 2>/dev/null | xargs)

log_info "Long-running queries (>5 min): $LONG_QUERIES"

echo ""
log_info "Step 5: Terminating stuck database sessions..."

if [ "$LONG_QUERIES" -gt 0 ]; then
    log_warning "Found $LONG_QUERIES long-running queries, terminating them..."
    
    # Show the queries before terminating
    sudo -u postgres psql -d "$DB_NAME" -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND state != 'idle' 
AND now() - query_start > interval '5 minutes';"
    
    # Terminate long-running queries
    TERMINATED=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND state != 'idle' 
AND now() - query_start > interval '5 minutes';" 2>/dev/null | grep -c "t" || echo "0")
    
    log_success "Terminated $TERMINATED stuck database sessions"
else
    log_info "No long-running queries found"
fi

# Terminate any remaining connections from killed processes
log_info "Cleaning up any remaining connections..."
sudo -u postgres psql -d "$DB_NAME" -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND application_name LIKE '%python%'
AND state = 'idle in transaction';" > /dev/null 2>&1 || true

echo ""
log_info "Step 6: Optimizing database performance..."

# Run VACUUM ANALYZE to optimize database
log_info "Running VACUUM ANALYZE to optimize database..."
sudo -u postgres psql -d "$DB_NAME" -c "VACUUM ANALYZE;" && log_success "Database optimization completed"

# Check database stats
TOTAL_CONNECTIONS=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';" | xargs)
log_info "Current total connections: $TOTAL_CONNECTIONS"

echo ""
log_info "Step 7: Starting services..."

sudo systemctl start gunicorn && log_success "Started Gunicorn" || log_error "Failed to start Gunicorn"
sleep 2
sudo systemctl start nginx && log_success "Started Nginx" || log_error "Failed to start Nginx"

echo ""
log_info "Step 8: Final health check..."

sleep 5

# Check service status
if sudo systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn is running"
else
    log_error "Gunicorn failed to start"
    log_info "Check logs: sudo journalctl -u gunicorn -n 20"
fi

if sudo systemctl is-active --quiet nginx; then
    log_success "Nginx is running"
else
    log_error "Nginx failed to start"
fi

# Test web connectivity
if curl -f http://localhost/ > /dev/null 2>&1; then
    log_success "✨ Website is responding!"
else
    log_warning "Website not responding yet. Checking service logs..."
    log_info "Gunicorn status: $(sudo systemctl is-active gunicorn)"
    log_info "Nginx status: $(sudo systemctl is-active nginx)"
fi

echo ""
log_success "🎉 PostgreSQL lock fix completed!"
log_info "Database: $DB_NAME"
log_info "Services: Gunicorn + Nginx restarted"
log_info "Total connections: $TOTAL_CONNECTIONS"

echo ""
echo -e "${CYAN}🔧 Manual verification commands:${NC}"
echo "  sudo systemctl status gunicorn"
echo "  sudo systemctl status nginx"
echo "  sudo journalctl -u gunicorn -f"
echo "  curl http://localhost/" 