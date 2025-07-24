# Open Science Tracker - VPS Deployment & Data Ingestion Guide

## Table of Contents
1. [VPS Environment Setup](#vps-environment-setup)
2. [Application Deployment](#application-deployment)
3. [Database Configuration](#database-configuration)
4. [Automated Data Ingestion](#automated-data-ingestion)
5. [File Monitoring System](#file-monitoring-system)
6. [Process Automation](#process-automation)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## VPS Environment Setup

### 1. System Requirements
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib nginx supervisor redis-server

# Install Node.js (for potential frontend builds)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. User & Directory Setup
```bash
# Your user should already exist (xeradb)
# Create directory structure
mkdir -p ~/epmc_monthly_data
mkdir -p ~/transparency_results
mkdir -p ~/logs
mkdir -p ~/backups

# Set proper permissions
chmod 755 ~/epmc_monthly_data
chmod 755 ~/transparency_results
chmod 755 ~/logs
```

---

## Application Deployment

### 1. Clone & Setup Application
```bash
# Navigate to web directory
cd /var/www/ost

# Your repository should already be cloned here
# Pull latest changes if needed
git pull origin main

# Activate virtual environment
source ost_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Create environment file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://ost_user:Choxos10203040@localhost:5432/ost_production

# Security Settings
SECRET_KEY=d8!tc5jn@nzsjmt-l+*9=m-6xq02)+p&^hy+pt+lg+2v$%=r=n
DEBUG=False
ALLOWED_HOSTS=ost.xeradb.com,www.xeradb.com,91.99.161.136,localhost,127.0.0.1

# Data Directories
EPMC_DATA_DIR=/home/xeradb/epmc_monthly_data/
TRANSPARENCY_DATA_DIR=/home/xeradb/transparency_results/

# Email Configuration (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ahmad.pub@gmail.com
EMAIL_HOST_PASSWORD=Choxos0874!*)@&)

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/ost/logs/ost.log
EOF

# Generate secret key
python -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())" >> .env

# Load environment variables
source .env
```

### 3. Environment Configuration
```bash
# Your Django settings should already be configured correctly
# The current settings.py handles both development and production automatically
# using environment variables and database URL detection
```

---

## Database Configuration

### 1. PostgreSQL Setup
```bash
# You should already have a database created
# If you need to recreate it:
sudo su - postgres

# Create database and user (if they don't exist)
createuser --interactive --pwprompt ost_user
# Enter password when prompted
createdb --owner=ost_user ost_production

# Grant privileges
psql -c "GRANT ALL PRIVILEGES ON DATABASE ost_production TO ost_user;"
psql -c "ALTER USER ost_user CREATEDB;"

# Exit postgres user
exit
```

### 2. Database Migration
```bash
# Navigate to project directory
cd /var/www/ost
source ost_env/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## Automated Data Ingestion

### 1. Enhanced Management Commands

Create `tracker/management/commands/process_epmc_files.py`:
```python
import os
import logging
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import Journal, Paper
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process EPMC data files and import into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file to process',
        )
        parser.add_argument(
            '--directory',
            type=str,
            default=getattr(settings, 'EPMC_DATA_DIR', '/home/ost/data/epmc_monthly_data'),
            help='Directory to scan for EPMC files',
        )

    def handle(self, *args, **options):
        directory = options['directory']
        specific_file = options['file']
        
        if specific_file:
            files_to_process = [specific_file]
        else:
            # Find all CSV files that haven't been processed
            files_to_process = self.find_unprocessed_files(directory)
        
        for file_path in files_to_process:
            try:
                self.process_epmc_file(file_path)
                self.mark_file_as_processed(file_path)
                logger.info(f"Successfully processed: {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {file_path}: {str(e)}")
                )

    def find_unprocessed_files(self, directory):
        """Find CSV files that haven't been processed yet"""
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        # Load list of already processed files
        processed_files = set()
        if os.path.exists(processed_files_log):
            with open(processed_files_log, 'r') as f:
                processed_files = set(line.strip() for line in f)
        
        # Find all CSV files
        all_files = []
        for filename in os.listdir(directory):
            if filename.endswith('.csv') and filename.startswith('epmc_'):
                file_path = os.path.join(directory, filename)
                if file_path not in processed_files:
                    all_files.append(file_path)
        
        return sorted(all_files)

    def process_epmc_file(self, file_path):
        """Process a single EPMC CSV file"""
        self.stdout.write(f"Processing: {file_path}")
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Validate required columns
        required_columns = ['id', 'source', 'title', 'authorString', 'journalTitle']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Process each row
        papers_created = 0
        papers_updated = 0
        
        for _, row in df.iterrows():
            try:
                # Get or create journal
                journal = None
                if pd.notna(row.get('journalTitle')):
                    journal, _ = Journal.objects.get_or_create(
                        title_full=row['journalTitle'],
                        defaults={
                            'title_abbreviation': row['journalTitle'][:50],
                        }
                    )
                
                # Prepare paper data
                paper_data = {
                    'source': row.get('source', 'PMC'),
                    'title': row.get('title', '')[:500],  # Truncate if too long
                    'author_string': row.get('authorString', '')[:1000],
                    'journal': journal,
                    'journal_title': row.get('journalTitle', ''),
                    'journal_issn': row.get('journalIssn', ''),
                    'pub_year': self.extract_year(row.get('firstPublicationDate')),
                    'pmid': row.get('pmid', ''),
                    'pmcid': row.get('pmcid', ''),
                    'doi': row.get('doi', ''),
                    'is_open_access': row.get('isOpenAccess', 'N') == 'Y',
                    'in_epmc': row.get('inEPMC', 'N') == 'Y',
                    'in_pmc': row.get('inPMC', 'N') == 'Y',
                    'has_pdf': row.get('hasPDF', 'N') == 'Y',
                    'first_publication_date': self.parse_date(row.get('firstPublicationDate')),
                    'first_index_date': self.parse_date(row.get('firstIndexDate')),
                }
                
                # Create or update paper
                paper, created = Paper.objects.update_or_create(
                    epmc_id=row['id'],
                    defaults=paper_data
                )
                
                if created:
                    papers_created += 1
                else:
                    papers_updated += 1
                    
            except Exception as e:
                logger.error(f"Error processing row with ID {row.get('id', 'unknown')}: {str(e)}")
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {file_path}: {papers_created} created, {papers_updated} updated"
            )
        )

    def extract_year(self, date_string):
        """Extract year from date string"""
        if pd.isna(date_string):
            return None
        try:
            return int(str(date_string)[:4])
        except (ValueError, TypeError):
            return None

    def parse_date(self, date_string):
        """Parse date string to datetime object"""
        if pd.isna(date_string):
            return None
        try:
            return datetime.strptime(str(date_string)[:10], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    def mark_file_as_processed(self, file_path):
        """Mark file as processed in log"""
        directory = os.path.dirname(file_path)
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        with open(processed_files_log, 'a') as f:
            f.write(f"{file_path}\n")
```

Create `tracker/management/commands/process_transparency_files.py`:
```python
import os
import logging
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import Paper
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process transparency results files and update paper records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file to process',
        )
        parser.add_argument(
            '--directory',
            type=str,
            default=getattr(settings, 'TRANSPARENCY_DATA_DIR', '/home/ost/data/transparency_results'),
            help='Directory to scan for transparency files',
        )

    def handle(self, *args, **options):
        directory = options['directory']
        specific_file = options['file']
        
        if specific_file:
            files_to_process = [specific_file]
        else:
            files_to_process = self.find_unprocessed_files(directory)
        
        for file_path in files_to_process:
            try:
                self.process_transparency_file(file_path)
                self.mark_file_as_processed(file_path)
                logger.info(f"Successfully processed: {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {file_path}: {str(e)}")
                )

    def find_unprocessed_files(self, directory):
        """Find transparency files that haven't been processed yet"""
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        processed_files = set()
        if os.path.exists(processed_files_log):
            with open(processed_files_log, 'r') as f:
                processed_files = set(line.strip() for line in f)
        
        all_files = []
        for filename in os.listdir(directory):
            if filename.endswith('.csv') and filename.startswith('transparency_'):
                file_path = os.path.join(directory, filename)
                if file_path not in processed_files:
                    all_files.append(file_path)
        
        return sorted(all_files)

    def process_transparency_file(self, file_path):
        """Process a single transparency results CSV file"""
        self.stdout.write(f"Processing: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Validate required columns
        required_columns = ['pmid', 'pmcid']  # At least one ID column
        if not any(col in df.columns for col in required_columns):
            raise ValueError("File must contain either 'pmid' or 'pmcid' column")
        
        papers_updated = 0
        papers_not_found = 0
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    # Find paper by PMID or PMCID
                    paper = None
                    
                    if pd.notna(row.get('pmid')):
                        try:
                            paper = Paper.objects.get(pmid=str(row['pmid']))
                        except Paper.DoesNotExist:
                            pass
                    
                    if not paper and pd.notna(row.get('pmcid')):
                        try:
                            paper = Paper.objects.get(pmcid=str(row['pmcid']))
                        except Paper.DoesNotExist:
                            pass
                    
                    if not paper:
                        papers_not_found += 1
                        continue
                    
                    # Update transparency indicators
                    updated = False
                    
                    if 'is_coi_pred' in row and pd.notna(row['is_coi_pred']):
                        paper.is_coi_pred = bool(row['is_coi_pred'])
                        updated = True
                    
                    if 'is_fund_pred' in row and pd.notna(row['is_fund_pred']):
                        paper.is_fund_pred = bool(row['is_fund_pred'])
                        updated = True
                    
                    if 'is_register_pred' in row and pd.notna(row['is_register_pred']):
                        paper.is_register_pred = bool(row['is_register_pred'])
                        updated = True
                    
                    if 'is_open_data' in row and pd.notna(row['is_open_data']):
                        paper.is_open_data = bool(row['is_open_data'])
                        updated = True
                    
                    if 'is_open_code' in row and pd.notna(row['is_open_code']):
                        paper.is_open_code = bool(row['is_open_code'])
                        updated = True
                    
                    # Update text fields if available
                    if 'coi_text' in row and pd.notna(row['coi_text']):
                        paper.coi_text = str(row['coi_text'])[:1000]
                        updated = True
                    
                    if 'fund_text' in row and pd.notna(row['fund_text']):
                        paper.fund_text = str(row['fund_text'])[:1000]
                        updated = True
                    
                    if 'register_text' in row and pd.notna(row['register_text']):
                        paper.register_text = str(row['register_text'])[:1000]
                        updated = True
                    
                    if updated:
                        # Calculate transparency score
                        score = 0
                        score += 1 if paper.is_open_data else 0
                        score += 1 if paper.is_open_code else 0
                        score += 1 if paper.is_coi_pred else 0
                        score += 1 if paper.is_fund_pred else 0
                        score += 1 if paper.is_register_pred else 0
                        score += 1 if paper.is_open_access else 0
                        
                        paper.transparency_score = score
                        paper.transparency_processed = True
                        paper.save()
                        papers_updated += 1
                        
                except Exception as e:
                    logger.error(f"Error processing transparency data for row: {str(e)}")
                    continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {file_path}: {papers_updated} papers updated, {papers_not_found} not found"
            )
        )

    def mark_file_as_processed(self, file_path):
        """Mark file as processed in log"""
        directory = os.path.dirname(file_path)
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        with open(processed_files_log, 'a') as f:
            f.write(f"{file_path}\n")
```

---

## File Monitoring System

### 1. Create File Watcher Script

Create `scripts/data_monitor.py`:
```python
#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import django

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ost/logs/data_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataFileHandler(FileSystemEventHandler):
    def __init__(self, file_type, command_name):
        self.file_type = file_type
        self.command_name = command_name
        self.processing_files = set()  # Track files being processed
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self.should_process_file(file_path):
            logger.info(f"New {self.file_type} file detected: {file_path}")
            # Wait a moment for file to be fully written
            time.sleep(5)
            self.process_file(file_path)
    
    def on_moved(self, event):
        if event.is_directory:
            return
        
        file_path = event.dest_path
        if self.should_process_file(file_path):
            logger.info(f"New {self.file_type} file moved: {file_path}")
            time.sleep(2)
            self.process_file(file_path)
    
    def should_process_file(self, file_path):
        """Check if file should be processed"""
        if not file_path.endswith('.csv'):
            return False
        
        filename = os.path.basename(file_path)
        
        if self.file_type == 'EPMC':
            return filename.startswith('epmc_') or filename.startswith('epmc_db_')
        elif self.file_type == 'transparency':
            return filename.startswith('transparency_')
        
        return False
    
    def process_file(self, file_path):
        """Process the detected file"""
        if file_path in self.processing_files:
            logger.info(f"File {file_path} is already being processed, skipping")
            return
        
        try:
            self.processing_files.add(file_path)
            
            # Check if file is complete (no longer being written to)
            if not self.is_file_complete(file_path):
                logger.info(f"File {file_path} is still being written, waiting...")
                time.sleep(10)
                if not self.is_file_complete(file_path):
                    logger.warning(f"File {file_path} may still be incomplete, processing anyway")
            
            # Run Django management command
            logger.info(f"Processing {file_path} with command: {self.command_name}")
            
            cmd = [
                '/home/ost/applications/OpenScienceTracker/ost_env/bin/python',
                '/home/ost/applications/OpenScienceTracker/manage.py',
                self.command_name,
                '--file', file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd='/home/ost/applications/OpenScienceTracker'
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully processed {file_path}")
                logger.info(f"Command output: {result.stdout}")
                
                # Move processed file to archive directory
                self.archive_file(file_path)
            else:
                logger.error(f"Error processing {file_path}: {result.stderr}")
            
        except Exception as e:
            logger.error(f"Exception processing {file_path}: {str(e)}")
        finally:
            self.processing_files.discard(file_path)
    
    def is_file_complete(self, file_path):
        """Check if file is complete by comparing sizes over time"""
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(2)
            size2 = os.path.getsize(file_path)
            return size1 == size2
        except OSError:
            return False
    
    def archive_file(self, file_path):
        """Move processed file to archive directory"""
        try:
            archive_dir = os.path.join(os.path.dirname(file_path), 'processed')
            os.makedirs(archive_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            archive_path = os.path.join(archive_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            
            os.rename(file_path, archive_path)
            logger.info(f"Archived {file_path} to {archive_path}")
        except Exception as e:
            logger.error(f"Error archiving {file_path}: {str(e)}")

def main():
    # Directories to monitor
    epmc_dir = '/home/ost/data/epmc_monthly_data'
    transparency_dir = '/home/ost/data/transparency_results'
    
    # Create directories if they don't exist
    os.makedirs(epmc_dir, exist_ok=True)
    os.makedirs(transparency_dir, exist_ok=True)
    
    # Create event handlers
    epmc_handler = DataFileHandler('EPMC', 'process_epmc_files')
    transparency_handler = DataFileHandler('transparency', 'process_transparency_files')
    
    # Create observer
    observer = Observer()
    observer.schedule(epmc_handler, epmc_dir, recursive=False)
    observer.schedule(transparency_handler, transparency_dir, recursive=False)
    
    # Start monitoring
    observer.start()
    logger.info("Data file monitoring started")
    logger.info(f"Monitoring EPMC files in: {epmc_dir}")
    logger.info(f"Monitoring transparency files in: {transparency_dir}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Data file monitoring stopped")
    
    observer.join()

if __name__ == "__main__":
    main()
```

### 2. Manual Processing Script

Create `scripts/manual_process.py`:
```python
#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
import django

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from django.core.management import call_command

def main():
    parser = argparse.ArgumentParser(description='Manually process data files')
    parser.add_argument('--epmc', action='store_true', help='Process all EPMC files')
    parser.add_argument('--transparency', action='store_true', help='Process all transparency files')
    parser.add_argument('--all', action='store_true', help='Process all files')
    parser.add_argument('--file', type=str, help='Process specific file')
    
    args = parser.parse_args()
    
    if args.all or args.epmc:
        print("Processing EPMC files...")
        call_command('process_epmc_files')
    
    if args.all or args.transparency:
        print("Processing transparency files...")
        call_command('process_transparency_files')
    
    if args.file:
        if 'epmc' in args.file:
            call_command('process_epmc_files', file=args.file)
        elif 'transparency' in args.file:
            call_command('process_transparency_files', file=args.file)
        else:
            print("Cannot determine file type from filename")

if __name__ == "__main__":
    main()
```

---

## Process Automation

### 1. Systemd Service for File Monitoring

Create `/etc/systemd/system/ost-data-monitor.service`:
```ini
[Unit]
Description=Open Science Tracker Data Monitor
After=network.target postgresql.service

[Service]
Type=simple
User=xeradb
Group=xeradb
WorkingDirectory=/var/www/ost
Environment=DJANGO_SETTINGS_MODULE=ost_web.settings
ExecStart=/var/www/ost/ost_env/bin/python /var/www/ost/scripts/data_monitor.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Systemd Service for Web Application

Create `/etc/systemd/system/ost-web.service`:
```ini
[Unit]
Description=Open Science Tracker Web Application
After=network.target postgresql.service

[Service]
Type=exec
User=ost
Group=ost
WorkingDirectory=/var/www/ost
Environment=DJANGO_SETTINGS_MODULE=ost_web.settings
ExecStart=/var/www/ost/ost_env/bin/activate && /var/www/ost/ost_env/bin/gunicorn ost_web.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. Cron Jobs for Maintenance

```bash
# Edit crontab for ost user
crontab -e

# Add these entries:
# Daily backup at 2 AM
0 2 * * * /var/www/ost/scripts/backup_database.sh

# Weekly cleanup of old processed files (older than 30 days)
0 3 * * 0 find /home/ost/data/*/processed -name "*.csv" -mtime +30 -delete

# Monthly statistics update
0 4 1 * * /var/www/ost/ost_env/bin/python /var/www/ost/manage.py update_statistics

# Check for unprocessed files every hour
0 * * * * /var/www/ost/scripts/check_unprocessed.sh
```

### 4. Backup Script

Create `scripts/backup_database.sh`:
```bash
#!/bin/bash

# Database backup script
BACKUP_DIR="/home/ost/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="ost_database"
DB_USER="ost_user"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME > $BACKUP_DIR/ost_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/ost_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "ost_backup_*.sql.gz" -mtime +7 -delete

# Log backup completion
echo "$(date): Database backup completed: ost_backup_$DATE.sql.gz" >> /home/ost/logs/backup.log
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/ost`:
```nginx
server {
    listen 80;
    server_name ost.xeradb.com www.xeradb.com 91.99.161.136;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ost.xeradb.com www.xeradb.com 91.99.161.136;
    
    # SSL Configuration (you'll need to obtain certificates)
    ssl_certificate /etc/letsencrypt/live/ost.xeradb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ost.xeradb.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Static files
    location /static/ {
        alias /var/www/ost/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /var/www/ost/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## Monitoring & Maintenance

### 1. Health Check Script

Create `scripts/health_check.py`:
```python
#!/usr/bin/env python3
import os
import sys
import requests
import psycopg2
import subprocess
from pathlib import Path

def check_web_service():
    """Check if web service is responding"""
    try:
        response = requests.get('http://localhost:8000/health/', timeout=10)
        return response.status_code == 200
    except:
        return False

def check_database():
    """Check database connectivity"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='ost_database',
            user='ost_user',
            password=os.getenv('DB_PASSWORD')
        )
        conn.close()
        return True
    except:
        return False

def check_data_monitor():
    """Check if data monitor service is running"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'ost-data-monitor'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == 'active'
    except:
        return False

def main():
    status = {
        'web_service': check_web_service(),
        'database': check_database(),
        'data_monitor': check_data_monitor(),
    }
    
    all_good = all(status.values())
    
    # Log status
    with open('/home/ost/logs/health_check.log', 'a') as f:
        f.write(f"{datetime.now()}: {status}\n")
    
    if not all_good:
        # Send alert (implement your preferred alerting method)
        print("ALERT: Some services are down!")
        for service, healthy in status.items():
            if not healthy:
                print(f"- {service}: DOWN")
    
    sys.exit(0 if all_good else 1)

if __name__ == "__main__":
    from datetime import datetime
    main()
```

### 2. Log Rotation

Create `/etc/logrotate.d/ost`:
```
/home/ost/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ost ost
    postrotate
        systemctl reload ost-web
        systemctl reload ost-data-monitor
    endscript
}
```

---

## Deployment Steps

### 1. Install and Configure Services
```bash
# Copy files to VPS
scp -r . ost@your-vps:/home/ost/applications/OpenScienceTracker/

# SSH to VPS
ssh ost@your-vps

# Setup environment
cd ~/applications/OpenScienceTracker
source ost_env/bin/activate
pip install -r requirements.txt
pip install watchdog schedule psycopg2-binary gunicorn

# Create management commands
mkdir -p tracker/management/commands
# (Copy the command files created above)

# Make scripts executable
chmod +x scripts/*.py
chmod +x scripts/*.sh

# Copy systemd service files (as root)
sudo cp /var/www/ost/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable ost-web
sudo systemctl enable ost-data-monitor
sudo systemctl start ost-web
sudo systemctl start ost-data-monitor

# Setup nginx
sudo cp /home/ost/applications/OpenScienceTracker/nginx/ost /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/ost /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Test the System
```bash
# Test manual processing
python scripts/manual_process.py --all

# Copy a test file to trigger automatic processing
cp test_data/epmc_test.csv ~/data/epmc_monthly_data/
cp test_data/transparency_test.csv ~/data/transparency_results/

# Check logs
tail -f ~/logs/data_monitor.log
tail -f ~/logs/ost.log

# Check service status
sudo systemctl status ost-web
sudo systemctl status ost-data-monitor
```

---

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Fix file permissions
   chown -R ost:ost /home/ost/
   chmod 755 /home/ost/data/*/
   chmod +x /home/ost/applications/OpenScienceTracker/scripts/*
   ```

2. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test connection
   psql -h localhost -U ost_user -d ost_database
   ```

3. **File Processing Stuck**
   ```bash
   # Check for stuck processes
   ps aux | grep python
   
   # Restart data monitor
   sudo systemctl restart ost-data-monitor
   ```

4. **Memory Issues**
   ```bash
   # Monitor memory usage
   free -h
   
   # Check for memory leaks
   sudo journalctl -u ost-web -f
   ```

### Log Locations
- Application logs: `/home/ost/logs/ost.log`
- Data monitor logs: `/home/ost/logs/data_monitor.log`
- Backup logs: `/home/ost/logs/backup.log`
- Health check logs: `/home/ost/logs/health_check.log`
- System logs: `sudo journalctl -u ost-web -f`

### Monitoring Commands
```bash
# Check service status
sudo systemctl status ost-web ost-data-monitor

# View real-time logs
tail -f ~/logs/*.log

# Check processing queues
ls -la ~/data/epmc_monthly_data/
ls -la ~/data/transparency_results/

# Database statistics
psql -h localhost -U ost_user -d ost_database -c "SELECT COUNT(*) FROM tracker_paper;"
```

---

## Data File Formats

### Expected EPMC File Format (`epmc_YYYY_MM.csv`):
```csv
id,source,title,authorString,journalTitle,journalIssn,pmid,pmcid,doi,isOpenAccess,inEPMC,inPMC,hasPDF,firstPublicationDate,firstIndexDate
PMC123456,PMC,"Sample Title","Author A, Author B","Sample Journal",1234-5678,12345678,PMC123456,10.1000/sample,Y,Y,Y,Y,2024-01-15,2024-01-16
```

### Expected Transparency File Format (`transparency_YYYY_MM.csv`):
```csv
pmid,pmcid,is_coi_pred,is_fund_pred,is_register_pred,is_open_data,is_open_code,coi_text,fund_text,register_text
12345678,PMC123456,1,1,0,1,0,"Conflict of interest text","Funding information","Registration details"
```

---

This comprehensive guide provides everything needed to deploy and maintain your Open Science Tracker on a VPS with automated data ingestion. The system will automatically process new files as they arrive and maintain a robust, scalable research transparency platform. 