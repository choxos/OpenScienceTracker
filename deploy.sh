#!/bin/bash

# ==============================================================================
# Open Science Tracker - Automated Deployment Script
# ==============================================================================
# This script automates the deployment of OST to your VPS server
# Usage: ./deploy.sh [--production|--staging] [--skip-backup] [--force]
#
# Author: Ahmad Sofi-Mahmudi
# Project: Open Science Tracker
# Year: 2025
# ==============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="OpenScienceTracker"
PROJECT_DIR="/var/www/ost"
VENV_DIR="$PROJECT_DIR/ost_env"
BACKUP_DIR="/var/backups/ost"
LOG_FILE="/var/log/ost_deploy.log"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
DJANGO_SETTINGS="ost_web.settings"

# Service names (adjust according to your server setup)
NGINX_SERVICE="nginx"
GUNICORN_SERVICE="ost-gunicorn"  # or whatever your Gunicorn service is named
SUPERVISOR_PROGRAM="ost"  # if using supervisor

# Default values
ENVIRONMENT="production"
SKIP_BACKUP=false
FORCE_DEPLOY=false
BRANCH="main"

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${WHITE}  $1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

print_step() {
    echo -e "${CYAN}➤ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check if running as appropriate user
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Consider using a dedicated user for deployment."
    fi
    
    # Check if project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory $PROJECT_DIR does not exist!"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment $VENV_DIR does not exist!"
        exit 1
    fi
    
    # Check if Python and pip are available
    if [ ! -f "$PYTHON_BIN" ]; then
        print_error "Python binary not found at $PYTHON_BIN"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        print_warning "Skipping backup as requested"
        return
    fi
    
    print_step "Creating backup..."
    
    # Create backup directory if it doesn't exist
    sudo mkdir -p "$BACKUP_DIR"
    
    # Create timestamped backup
    BACKUP_NAME="ost_backup_$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    # Backup database (PostgreSQL)
    print_step "Backing up database..."
    sudo -u postgres pg_dump ost_database > "$BACKUP_PATH.sql" 2>/dev/null || {
        print_warning "Database backup failed, continuing anyway..."
    }
    
    # Backup static files and media
    print_step "Backing up static files..."
    sudo tar -czf "$BACKUP_PATH.tar.gz" -C "$PROJECT_DIR" static staticfiles media 2>/dev/null || {
        print_warning "Static files backup failed, continuing anyway..."
    }
    
    # Keep only last 10 backups
    sudo find "$BACKUP_DIR" -name "ost_backup_*" -type f | sort | head -n -10 | sudo xargs rm -f
    
    print_success "Backup created: $BACKUP_NAME"
    log_message "Backup created: $BACKUP_NAME"
}

pull_latest_code() {
    print_step "Pulling latest code from Git..."
    
    cd "$PROJECT_DIR"
    
    # Fix Git ownership issues (common on VPS deployments)
    print_step "Configuring Git safe directory..."
    sudo git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
    
    # Fix logging permissions (prevent Django startup errors)
    print_step "Setting up logging permissions..."
    sudo mkdir -p /var/log/ost 2>/dev/null || true
    mkdir -p "$PROJECT_DIR/logs" 2>/dev/null || true
    sudo chown -R $USER:www-data /var/log/ost 2>/dev/null || true
    sudo chown -R $USER:www-data "$PROJECT_DIR/logs" 2>/dev/null || true
    sudo chmod -R 775 /var/log/ost 2>/dev/null || true
    chmod -R 775 "$PROJECT_DIR/logs" 2>/dev/null || true
    
    # Stash any local changes
    sudo git stash save "Auto-stash before deployment $(date)" 2>/dev/null || true
    
    # Fetch latest changes
    sudo git fetch origin
    
    # Check if there are updates
    LOCAL=$(sudo git rev-parse HEAD)
    REMOTE=$(sudo git rev-parse origin/$BRANCH)
    
    if [ "$LOCAL" = "$REMOTE" ] && [ "$FORCE_DEPLOY" = false ]; then
        print_warning "No new changes to deploy. Use --force to deploy anyway."
        exit 0
    fi
    
    # Pull latest changes
    sudo git checkout "$BRANCH"
    sudo git pull origin "$BRANCH"
    
    # Get commit info
    COMMIT_HASH=$(sudo git rev-parse --short HEAD)
    COMMIT_MSG=$(sudo git log -1 --pretty=%B)
    
    print_success "Updated to commit: $COMMIT_HASH"
    print_step "Latest commit: $COMMIT_MSG"
    log_message "Deployed commit: $COMMIT_HASH - $COMMIT_MSG"
}

update_dependencies() {
    print_step "Updating Python dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Activate virtual environment and update dependencies
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip first
    $PIP_BIN install --upgrade pip
    
    # Install/update requirements
    if [ -f "requirements.txt" ]; then
        $PIP_BIN install -r requirements.txt --upgrade
        print_success "Dependencies updated from requirements.txt"
    else
        print_warning "requirements.txt not found, skipping dependency update"
    fi
    
    deactivate
}

run_django_commands() {
    print_step "Running Django management commands..."
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Set Django settings
    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS"
    
    # Run migrations
    print_step "Running database migrations..."
    $PYTHON_BIN manage.py migrate --noinput
    print_success "Migrations completed"
    
    # Collect static files
    print_step "Collecting static files..."
    $PYTHON_BIN manage.py collectstatic --noinput --clear
    print_success "Static files collected"
    
    # Clear cache if using cache framework
    print_step "Clearing Django cache..."
    $PYTHON_BIN manage.py shell -c "from django.core.cache import cache; cache.clear()" 2>/dev/null || {
        print_warning "Cache clearing failed or not configured"
    }
    
    # Run any custom management commands
    if [ -f "deploy_commands.txt" ]; then
        print_step "Running custom management commands..."
        while IFS= read -r command; do
            if [[ ! "$command" =~ ^#.*$ ]] && [[ -n "$command" ]]; then
                print_step "Running: $command"
                $PYTHON_BIN manage.py $command
            fi
        done < deploy_commands.txt
        print_success "Custom commands executed"
    fi
    
    deactivate
}

restart_services() {
    print_step "Restarting services..."
    
    # Restart Gunicorn (if using systemd service)
    if systemctl is-active --quiet "$GUNICORN_SERVICE" 2>/dev/null; then
        print_step "Restarting Gunicorn service..."
        sudo systemctl restart "$GUNICORN_SERVICE"
        print_success "Gunicorn restarted"
    elif command -v supervisorctl >/dev/null 2>&1; then
        # Restart using supervisor
        print_step "Restarting application using Supervisor..."
        sudo supervisorctl restart "$SUPERVISOR_PROGRAM" 2>/dev/null || {
            print_warning "Supervisor restart failed, trying alternative methods..."
        }
    else
        print_warning "No service manager found. You may need to restart manually."
    fi
    
    # Restart Nginx
    print_step "Restarting Nginx..."
    sudo systemctl restart "$NGINX_SERVICE"
    print_success "Nginx restarted"
    
    # Wait a moment for services to start
    sleep 2
    
    # Check service status
    print_step "Checking service status..."
    if systemctl is-active --quiet "$NGINX_SERVICE"; then
        print_success "Nginx is running"
    else
        print_error "Nginx failed to start!"
    fi
    
    if systemctl is-active --quiet "$GUNICORN_SERVICE" 2>/dev/null; then
        print_success "Gunicorn is running"
    else
        print_warning "Gunicorn status unknown or not using systemd"
    fi
}

set_permissions() {
    print_step "Setting proper file permissions..."
    
    cd "$PROJECT_DIR"
    
    # Set ownership (adjust user:group as needed)
    sudo chown -R www-data:www-data "$PROJECT_DIR" 2>/dev/null || {
        print_warning "Could not set www-data ownership, trying current user..."
        sudo chown -R $(whoami):$(whoami) "$PROJECT_DIR"
    }
    
    # Set directory permissions
    sudo find "$PROJECT_DIR" -type d -exec chmod 755 {} \;
    
    # Set file permissions
    sudo find "$PROJECT_DIR" -type f -exec chmod 644 {} \;
    
    # Make manage.py executable
    sudo chmod +x "$PROJECT_DIR/manage.py"
    
    # Set secure permissions for sensitive files
    if [ -f "$PROJECT_DIR/.env" ]; then
        sudo chmod 600 "$PROJECT_DIR/.env"
    fi
    
    if [ -f "$PROJECT_DIR/ost_web/settings.py" ]; then
        sudo chmod 644 "$PROJECT_DIR/ost_web/settings.py"
    fi
    
    print_success "Permissions set"
}

run_health_check() {
    print_step "Running health checks..."
    
    # Check if Django can start
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    print_step "Testing Django configuration..."
    $PYTHON_BIN manage.py check --deploy 2>/dev/null || {
        print_warning "Django deployment check failed, running basic check..."
        $PYTHON_BIN manage.py check
    }
    
    deactivate
    
    # Check if website is responding (adjust URL as needed)
    SITE_URL="http://localhost"
    print_step "Testing website response..."
    
    if command -v curl >/dev/null 2>&1; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "Website is responding (HTTP $HTTP_CODE)"
        else
            print_warning "Website returned HTTP $HTTP_CODE"
        fi
    else
        print_warning "curl not available for health check"
    fi
    
    print_success "Health checks completed"
}

show_summary() {
    print_header "DEPLOYMENT SUMMARY"
    
    echo -e "${WHITE}Project:${NC} $PROJECT_NAME"
    echo -e "${WHITE}Environment:${NC} $ENVIRONMENT"
    echo -e "${WHITE}Branch:${NC} $BRANCH"
    echo -e "${WHITE}Deployed to:${NC} $PROJECT_DIR"
    echo -e "${WHITE}Time:${NC} $(date)"
    
    if [ -d "$PROJECT_DIR/.git" ]; then
        cd "$PROJECT_DIR"
        CURRENT_COMMIT=$(sudo git rev-parse --short HEAD)
        echo -e "${WHITE}Commit:${NC} $CURRENT_COMMIT"
    fi
    
    echo ""
    echo -e "${GREEN}🚀 Deployment completed successfully!${NC}"
    echo -e "${CYAN}📝 Check logs at: $LOG_FILE${NC}"
    echo -e "${CYAN}🌐 Website: http://your-domain.com${NC}"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --production    Deploy to production environment (default)"
    echo "  --staging       Deploy to staging environment"
    echo "  --skip-backup   Skip database and files backup"
    echo "  --force         Force deployment even if no changes"
    echo "  --branch BRANCH Specify git branch to deploy (default: main)"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Standard production deployment"
    echo "  $0 --staging --skip-backup  # Deploy to staging without backup"
    echo "  $0 --force --branch develop # Force deploy from develop branch"
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --production)
            ENVIRONMENT="production"
            shift
            ;;
        --staging)
            ENVIRONMENT="staging"
            PROJECT_DIR="/var/www/ost-staging"  # Adjust as needed
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main deployment process
main() {
    print_header "OST DEPLOYMENT STARTED"
    echo -e "${WHITE}Environment: $ENVIRONMENT${NC}"
    echo -e "${WHITE}Branch: $BRANCH${NC}"
    echo ""
    
    log_message "=== Deployment started for $ENVIRONMENT environment ==="
    
    # Run deployment steps
    check_prerequisites
    create_backup
    pull_latest_code
    update_dependencies
    run_django_commands
    set_permissions
    restart_services
    run_health_check
    show_summary
    
    log_message "=== Deployment completed successfully ==="
}

# Error handling
trap 'print_error "Deployment failed! Check $LOG_FILE for details."; log_message "Deployment failed with error"; exit 1' ERR

# Create log file if it doesn't exist
sudo touch "$LOG_FILE"
sudo chmod 644 "$LOG_FILE"

# Run main function
main

exit 0 