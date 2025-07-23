# 🌟 Xera DB Open Science Ecosystem Guide

Complete guide for organizing multiple open science web applications on a single Hetzner VPS.

## 🏗️ Architecture Overview

### Recommended VPS Configuration
- **VPS Type**: CAX31 or CAX41 (for multiple apps)
  - CAX31: 8 vCPU, 16GB RAM, 160GB SSD - $14.39/month
  - CAX41: 16 vCPU, 32GB RAM, 320GB SSD - $28.79/month
- **Operating System**: Ubuntu 22.04 LTS ARM64

### Domain Structure Strategy
```
xeradb.com                    # Main landing page & ecosystem overview
├── tracker.xeradb.com       # Open Science Tracker
├── retractions.xeradb.com   # Retractions Database
├── api.xeradb.com          # Shared API services (future)
├── docs.xeradb.com         # Documentation portal
├── dev.xeradb.com          # Development/staging environment
└── admin.xeradb.com        # System administration dashboard
```

## 📁 Directory Structure

### Root Organization
```
/var/www/
├── xeradb-main/             # Main landing page (React/Vue/Static)
├── ost/                     # Open Science Tracker (Django)
├── retractions/             # Retractions project (Django/Flask)
├── shared/                  # Shared resources
│   ├── scripts/             # Deployment & maintenance scripts
│   ├── configs/             # Shared configuration files
│   ├── ssl/                 # SSL certificates
│   └── logs/                # Centralized logging
├── staging/                 # Staging versions of all apps
│   ├── ost-staging/
│   └── retractions-staging/
└── backups/                 # Database & file backups
    ├── daily/
    ├── weekly/
    └── monthly/
```

### Per-Project Structure
```
/var/www/ost/               # Example project structure
├── app/                    # Django application
├── venv/                   # Python virtual environment
├── static/                 # Static files
├── media/                  # User uploads
├── logs/                   # Application logs
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
└── deploy.sh              # Deployment script
```

## 🗄️ Database Strategy

### PostgreSQL Organization
```sql
-- Separate databases for each project
CREATE DATABASE xeradb_main;
CREATE DATABASE ost_production;
CREATE DATABASE retractions_production;
CREATE DATABASE shared_services;

-- Staging databases
CREATE DATABASE ost_staging;
CREATE DATABASE retractions_staging;

-- Users per project
CREATE USER xeradb_main_user WITH PASSWORD 'secure_password';
CREATE USER ost_user WITH PASSWORD 'secure_password';
CREATE USER retractions_user WITH PASSWORD 'secure_password';

-- Shared user for cross-project queries (if needed)
CREATE USER shared_user WITH PASSWORD 'secure_password';
```

## 🌐 Nginx Configuration

### Main Nginx Structure
```
/etc/nginx/
├── sites-available/
│   ├── xeradb-main
│   ├── ost
│   ├── retractions
│   ├── api
│   └── staging
├── sites-enabled/          # Symlinks to enabled sites
├── ssl/                    # SSL configurations
└── conf.d/
    ├── rate-limiting.conf
    ├── security.conf
    └── gzip.conf
```

### Example Main Site Configuration
```nginx
# /etc/nginx/sites-available/xeradb-main
server {
    listen 80;
    server_name xeradb.com www.xeradb.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name xeradb.com www.xeradb.com;

    ssl_certificate /etc/letsencrypt/live/xeradb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xeradb.com/privkey.pem;
    
    root /var/www/xeradb-main/dist;
    index index.html;

    # Security headers
    include /etc/nginx/conf.d/security.conf;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy for ecosystem status
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        include proxy_params;
    }
}
```

### Project-Specific Configuration Template
```nginx
# /etc/nginx/sites-available/ost
server {
    listen 80;
    server_name tracker.xeradb.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tracker.xeradb.com;

    ssl_certificate /etc/letsencrypt/live/xeradb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xeradb.com/privkey.pem;

    client_max_body_size 100M;

    # Security headers
    include /etc/nginx/conf.d/security.conf;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
        
        # Add ecosystem headers
        add_header X-Powered-By "Xera-DB";
        add_header X-Project "OpenScienceTracker";
    }
}
```

## ⚙️ Systemd Services Organization

### Service Structure
```
/etc/systemd/system/
├── xeradb-ost.service           # Open Science Tracker
├── xeradb-retractions.service   # Retractions Database
├── xeradb-api.service           # Shared API (future)
├── xeradb-backup.service        # Backup service
└── xeradb-backup.timer          # Backup timer
```

### Example Service Template
```ini
# /etc/systemd/system/xeradb-ost.service
[Unit]
Description=Xera DB - Open Science Tracker
After=network.target postgresql.service

[Service]
User=xeradb
Group=xeradb
WorkingDirectory=/var/www/ost
Environment="PATH=/var/www/ost/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=ost_web.production_settings"
Environment="XERADB_PROJECT=ost"
ExecStart=/var/www/ost/venv/bin/gunicorn --config /var/www/ost/gunicorn.conf.py ost_web.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 🔐 SSL Certificate Management

### Wildcard Certificate Setup
```bash
# Install Certbot with DNS plugin (for wildcard certs)
sudo snap install certbot
sudo snap install certbot-dns-cloudflare

# Configure DNS credentials (example for Cloudflare)
sudo nano /etc/letsencrypt/cloudflare.ini
# dns_cloudflare_api_token = your_cloudflare_api_token

# Get wildcard certificate
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d xeradb.com \
  -d "*.xeradb.com"
```

## 🚀 Deployment Strategy

### Automated Deployment Script
```bash
#!/bin/bash
# /var/www/shared/scripts/deploy.sh

PROJECT=$1
BRANCH=${2:-main}

if [ -z "$PROJECT" ]; then
    echo "Usage: $0 <project> [branch]"
    echo "Available projects: ost, retractions, main"
    exit 1
fi

echo "🚀 Deploying $PROJECT from $BRANCH branch..."

case $PROJECT in
    "ost")
        cd /var/www/ost
        git pull origin $BRANCH
        source venv/bin/activate
        pip install -r requirements.txt
        python manage.py migrate
        python manage.py collectstatic --noinput
        sudo systemctl restart xeradb-ost
        ;;
    "retractions")
        cd /var/www/retractions
        git pull origin $BRANCH
        source venv/bin/activate
        pip install -r requirements.txt
        python manage.py migrate
        python manage.py collectstatic --noinput
        sudo systemctl restart xeradb-retractions
        ;;
    "main")
        cd /var/www/xeradb-main
        git pull origin $BRANCH
        npm install
        npm run build
        sudo systemctl reload nginx
        ;;
    *)
        echo "Unknown project: $PROJECT"
        exit 1
        ;;
esac

echo "✅ Deployment of $PROJECT completed!"
```

## 📊 Monitoring & Logging

### Centralized Logging
```bash
# Create log aggregation script
nano /var/www/shared/scripts/logs.sh
```

```bash
#!/bin/bash
# Quick log checking script

case $1 in
    "ost")
        sudo journalctl -u xeradb-ost -f
        ;;
    "retractions")
        sudo journalctl -u xeradb-retractions -f
        ;;
    "nginx")
        sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
        ;;
    "system")
        sudo journalctl -f
        ;;
    *)
        echo "Usage: $0 <ost|retractions|nginx|system>"
        ;;
esac
```

### System Monitoring Dashboard
```python
# /var/www/shared/monitor.py
import psutil
import subprocess
import json
from datetime import datetime

def get_system_status():
    """Get comprehensive system status for all projects"""
    return {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        },
        'services': {
            'ost': get_service_status('xeradb-ost'),
            'retractions': get_service_status('xeradb-retractions'),
            'nginx': get_service_status('nginx'),
            'postgresql': get_service_status('postgresql')
        },
        'databases': {
            'ost_size': get_db_size('ost_production'),
            'retractions_size': get_db_size('retractions_production')
        }
    }

def get_service_status(service_name):
    """Check if systemd service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except:
        return False
```

## 💾 Backup Strategy

### Comprehensive Backup Script
```bash
#!/bin/bash
# /var/www/shared/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/www/backups/daily"

echo "🔄 Starting Xera DB ecosystem backup..."

# Database backups
pg_dump -h localhost -U ost_user ost_production > $BACKUP_DIR/ost_$DATE.sql
pg_dump -h localhost -U retractions_user retractions_production > $BACKUP_DIR/retractions_$DATE.sql

# File backups
tar -czf $BACKUP_DIR/ost_files_$DATE.tar.gz /var/www/ost/media
tar -czf $BACKUP_DIR/retractions_files_$DATE.tar.gz /var/www/retractions/media

# Configuration backup
tar -czf $BACKUP_DIR/configs_$DATE.tar.gz /etc/nginx/sites-available /etc/systemd/system/xeradb-*

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed!"
```

## 🔧 Project Template

### Quick Setup for New Projects
```bash
#!/bin/bash
# /var/www/shared/scripts/new-project.sh

PROJECT_NAME=$1
PROJECT_TYPE=${2:-django}  # django, flask, node, static

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <project-name> [django|flask|node|static]"
    exit 1
fi

echo "🆕 Creating new project: $PROJECT_NAME"

# Create directory structure
mkdir -p /var/www/$PROJECT_NAME
cd /var/www/$PROJECT_NAME

case $PROJECT_TYPE in
    "django")
        python3 -m venv venv
        source venv/bin/activate
        pip install django gunicorn psycopg2-binary
        django-admin startproject ${PROJECT_NAME}_web .
        ;;
    "flask")
        python3 -m venv venv
        source venv/bin/activate
        pip install flask gunicorn psycopg2-binary
        ;;
    "node")
        npm init -y
        npm install express
        ;;
esac

# Create basic configurations
echo "PROJECT_NAME=$PROJECT_NAME" > .env
echo "DEBUG=True" >> .env

# Set permissions
sudo chown -R xeradb:xeradb /var/www/$PROJECT_NAME

echo "✅ Project $PROJECT_NAME created!"
echo "Next steps:"
echo "1. Configure database"
echo "2. Set up Nginx virtual host"
echo "3. Create systemd service"
echo "4. Configure SSL"
```

## 📈 Resource Management

### VPS Sizing Recommendations

| Projects | VPS Type | vCPU | RAM | Storage | Monthly Cost |
|----------|----------|------|-----|---------|--------------|
| 1-2      | CAX21    | 4    | 8GB | 80GB    | $7.39        |
| 3-4      | CAX31    | 8    | 16GB| 160GB   | $14.39       |
| 5+       | CAX41    | 16   | 32GB| 320GB   | $28.79       |

### Resource Monitoring
```bash
# Quick resource check
alias xeradb-status='echo "=== Xera DB System Status ===" && \
  df -h | grep -E "(Filesystem|/dev/)" && \
  free -h && \
  systemctl status xeradb-* --no-pager'
```

## 🎯 Implementation Steps

### Phase 1: Infrastructure Setup (1-2 hours)
1. Upgrade VPS to CAX31 if needed
2. Set up domain structure and DNS
3. Configure wildcard SSL certificates
4. Create directory structure

### Phase 2: Open Science Tracker Migration (30 mins)
1. Move existing OST to new directory structure
2. Update Nginx configuration for subdomain
3. Test and verify functionality

### Phase 3: Retractions Project Setup (1-2 hours)
1. Create new project structure
2. Set up database and environment
3. Configure Nginx virtual host
4. Create systemd service

### Phase 4: Ecosystem Integration (1 hour)
1. Create main landing page
2. Set up monitoring and logging
3. Configure automated backups
4. Create deployment scripts

### Phase 5: Documentation & Maintenance (30 mins)
1. Document all configurations
2. Create troubleshooting guides
3. Set up monitoring alerts

## 🚀 Getting Started

1. **Clone this ecosystem approach**:
   ```bash
   wget https://raw.githubusercontent.com/choxos/OpenScienceTracker/main/scripts/setup-ecosystem.sh
   chmod +x setup-ecosystem.sh
   ./setup-ecosystem.sh
   ```

2. **Follow the phase-by-phase implementation**
3. **Test each component thoroughly**
4. **Set up monitoring and backups**

---

**🌟 Result**: A scalable, maintainable ecosystem of open science applications under the Xera DB brand, all running efficiently on a single Hetzner VPS with proper isolation, monitoring, and backup strategies. 