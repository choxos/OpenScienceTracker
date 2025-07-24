#!/bin/bash

# Open Science Tracker Database Backup Script
# Author: Ahmad Sofi-Mahmudi
# Description: Creates automated PostgreSQL database backups with compression and retention management

# Configuration
BACKUP_DIR="/home/xeradb/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="ost_production"
DB_USER="ost_user"
DB_HOST="localhost"
LOG_FILE="/home/xeradb/logs/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG_FILE"
}

# Function to log colored messages to console
log_colored() {
    echo -e "${2}$(date '+%Y-%m-%d %H:%M:%S'): $1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG_FILE"
}

# Create necessary directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log_colored "Starting database backup for $DB_NAME" "$GREEN"

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log_colored "ERROR: PostgreSQL service is not running" "$RED"
    exit 1
fi

# Create database backup
BACKUP_FILE="$BACKUP_DIR/ost_backup_$DATE.sql"
log_message "Creating backup: $BACKUP_FILE"

# Perform the backup
if pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --verbose --no-password > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log_colored "Database dump completed successfully" "$GREEN"
    
    # Get file size before compression
    ORIGINAL_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_message "Original backup size: $ORIGINAL_SIZE"
    
    # Compress backup
    log_message "Compressing backup file..."
    if gzip "$BACKUP_FILE"; then
        COMPRESSED_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        log_colored "Backup compressed successfully: $COMPRESSED_SIZE" "$GREEN"
        
        # Verify compressed file exists and has content
        if [[ -f "$COMPRESSED_FILE" && -s "$COMPRESSED_FILE" ]]; then
            log_colored "Backup verification: PASSED" "$GREEN"
        else
            log_colored "ERROR: Backup verification failed - compressed file is empty or missing" "$RED"
            exit 1
        fi
    else
        log_colored "ERROR: Failed to compress backup file" "$RED"
        exit 1
    fi
else
    log_colored "ERROR: Database dump failed" "$RED"
    exit 1
fi

# Clean up old backups (keep last 7 days)
log_message "Cleaning up old backups (keeping last 7 days)..."
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "ost_backup_*.sql.gz" -mtime +7 2>/dev/null)
if [[ -n "$OLD_BACKUPS" ]]; then
    echo "$OLD_BACKUPS" | while read -r old_backup; do
        if rm "$old_backup"; then
            log_message "Removed old backup: $(basename "$old_backup")"
        else
            log_colored "WARNING: Failed to remove old backup: $(basename "$old_backup")" "$YELLOW"
        fi
    done
else
    log_message "No old backups to remove"
fi

# Generate backup report
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "ost_backup_*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log_message "Backup completed successfully!"
log_message "Total backups: $TOTAL_BACKUPS"
log_message "Total backup directory size: $TOTAL_SIZE"

# Optional: Send notification (uncomment if you have mail configured)
# echo "OST Database backup completed successfully on $(hostname) at $(date)" | mail -s "OST Backup Success" admin@example.com

log_colored "Database backup process completed successfully" "$GREEN"
exit 0 