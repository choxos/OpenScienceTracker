#!/bin/bash

# Database backup script for Open Science Tracker
# Author: Ahmad Sofi-Mahmudi
# Usage: ./backup_database.sh

BACKUP_DIR="/home/ost/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="ost_database"
DB_USER="ost_user"
LOG_FILE="/home/ost/logs/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date): $1" >> $LOG_FILE
    echo -e "$2$1$NC"
}

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log_message "ERROR: PostgreSQL is not running" $RED
    exit 1
fi

log_message "Starting database backup..." $YELLOW

# Create database backup
BACKUP_FILE="$BACKUP_DIR/ost_backup_$DATE.sql"

if pg_dump -h localhost -U $DB_USER -d $DB_NAME > $BACKUP_FILE 2>/dev/null; then
    log_message "Database backup created: $BACKUP_FILE" $GREEN
    
    # Compress backup
    if gzip $BACKUP_FILE; then
        COMPRESSED_FILE="$BACKUP_FILE.gz"
        log_message "Backup compressed: $COMPRESSED_FILE" $GREEN
        
        # Get file size
        SIZE=$(du -h $COMPRESSED_FILE | cut -f1)
        log_message "Backup size: $SIZE" $GREEN
        
        # Keep only last 7 days of backups
        DELETED_COUNT=$(find $BACKUP_DIR -name "ost_backup_*.sql.gz" -mtime +7 -delete -print | wc -l)
        if [ $DELETED_COUNT -gt 0 ]; then
            log_message "Cleaned up $DELETED_COUNT old backup(s)" $YELLOW
        fi
        
        # Verify backup integrity
        if gzip -t $COMPRESSED_FILE; then
            log_message "Backup integrity verified" $GREEN
            log_message "Database backup completed successfully: ost_backup_$DATE.sql.gz" $GREEN
        else
            log_message "ERROR: Backup integrity check failed" $RED
            exit 1
        fi
        
    else
        log_message "ERROR: Failed to compress backup" $RED
        exit 1
    fi
else
    log_message "ERROR: Failed to create database backup" $RED
    exit 1
fi

# Optional: Upload to cloud storage (uncomment and configure as needed)
# aws s3 cp $COMPRESSED_FILE s3://your-backup-bucket/ost-backups/
# rclone copy $COMPRESSED_FILE remote:backups/ost/ 