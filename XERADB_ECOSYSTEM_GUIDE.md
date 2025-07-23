# 🌟 Xera DB Open Science Ecosystem Guide

Complete guide for organizing multiple open science web applications on a single Hetzner VPS.

## 🏗️ Architecture Overview

### Xera DB Project Portfolio
**Xera DB** hosts a comprehensive suite of open science research applications:

1. **OST** - Open Science Tracker: Transparency indicators in scientific publications
2. **PRCT** - Post-Retraction Citation Tracker: Citation patterns after paper retractions
3. **CIHRPT** - CIHR Projects Tracker: Canadian Institutes of Health Research funding
4. **NHMRCPT** - NHMRC Projects Tracker: Australian National Health & Medical Research Council
5. **NIHRPT** - NIHR Projects Tracker: UK National Institute for Health Research
6. **NIHPT** - NIH Projects Tracker: US National Institutes of Health funding
7. **TTEdb** - Target Trial Emulation Database: Clinical trial methodology database
8. **DCPS** - Dental Caries Population Studies: Dental epidemiology research

### Recommended VPS Configuration
- **VPS Type**: CAX41 (for 8 applications)
  - CAX41: 16 vCPU, 32GB RAM, 320GB SSD - $28.79/month
  - Alternative CAX31: 8 vCPU, 16GB RAM, 160GB SSD - $14.39/month (for 3-5 apps)
- **Operating System**: Ubuntu 22.04 LTS ARM64

### Domain Structure Strategy
```
xeradb.com                    # Main landing page & ecosystem overview
├── ost.xeradb.com           # Open Science Tracker
├── prct.xeradb.com          # Post-Retraction Citation Tracker
├── cihrpt.xeradb.com        # CIHR Projects Tracker
├── nhmrcpt.xeradb.com       # NHMRC Projects Tracker  
├── nihrpt.xeradb.com        # NIHR Projects Tracker
├── nihpt.xeradb.com         # NIH Projects Tracker
├── ttedb.xeradb.com         # Target Trial Emulation Database
├── dcps.xeradb.com          # Dental Caries Population Studies
├── api.xeradb.com           # Shared API services
├── docs.xeradb.com          # Documentation portal
├── dev.xeradb.com           # Development/staging environment
└── admin.xeradb.com         # System administration dashboard
```

## 📁 Directory Structure

### Root Organization
```
/var/www/
├── xeradb-main/             # Main landing page (React/Vue/Static)
├── ost/                     # Open Science Tracker (Django)
├── prct/                    # Post-Retraction Citation Tracker (Django)
├── cihrpt/                  # CIHR Projects Tracker (Django)
├── nhmrcpt/                 # NHMRC Projects Tracker (Django)
├── nihrpt/                  # NIHR Projects Tracker (Django)
├── nihpt/                   # NIH Projects Tracker (Django)
├── ttedb/                   # Target Trial Emulation Database (Django)
├── dcps/                    # Dental Caries Population Studies (Django)
├── shared/                  # Shared resources
│   ├── scripts/             # Deployment & maintenance scripts
│   ├── configs/             # Shared configuration files
│   ├── ssl/                 # SSL certificates
│   └── logs/                # Centralized logging
├── staging/                 # Staging versions of all apps
│   ├── ost-staging/
│   ├── prct-staging/
│   ├── cihrpt-staging/
│   ├── nhmrcpt-staging/
│   ├── nihrpt-staging/
│   ├── nihpt-staging/
│   ├── ttedb-staging/
│   └── dcps-staging/
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
CREATE DATABASE prct_production;
CREATE DATABASE cihrpt_production;
CREATE DATABASE nhmrcpt_production;
CREATE DATABASE nihrpt_production;
CREATE DATABASE nihpt_production;
CREATE DATABASE ttedb_production;
CREATE DATABASE dcps_production;
CREATE DATABASE shared_services;

-- Staging databases
CREATE DATABASE ost_staging;
CREATE DATABASE prct_staging;
CREATE DATABASE cihrpt_staging;
CREATE DATABASE nhmrcpt_staging;
CREATE DATABASE nihrpt_staging;
CREATE DATABASE nihpt_staging;
CREATE DATABASE ttedb_staging;
CREATE DATABASE dcps_staging;

-- Users per project
CREATE USER xeradb_main_user WITH PASSWORD 'secure_password';
CREATE USER ost_user WITH PASSWORD 'secure_password';
CREATE USER prct_user WITH PASSWORD 'secure_password';
CREATE USER cihrpt_user WITH PASSWORD 'secure_password';
CREATE USER nhmrcpt_user WITH PASSWORD 'secure_password';
CREATE USER nihrpt_user WITH PASSWORD 'secure_password';
CREATE USER nihpt_user WITH PASSWORD 'secure_password';
CREATE USER ttedb_user WITH PASSWORD 'secure_password';
CREATE USER dcps_user WITH PASSWORD 'secure_password';

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
│   ├── prct
│   ├── cihrpt
│   ├── nhmrcpt
│   ├── nihrpt
│   ├── nihpt
│   ├── ttedb
│   ├── dcps
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
├── xeradb-prct.service          # Post-Retraction Citation Tracker
├── xeradb-cihrpt.service        # CIHR Projects Tracker
├── xeradb-nhmrcpt.service       # NHMRC Projects Tracker
├── xeradb-nihrpt.service        # NIHR Projects Tracker
├── xeradb-nihpt.service         # NIH Projects Tracker
├── xeradb-ttedb.service         # Target Trial Emulation Database
├── xeradb-dcps.service          # Dental Caries Population Studies
├── xeradb-api.service           # Shared API services
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
     echo "Available projects: ost, prct, cihrpt, nhmrcpt, nihrpt, nihpt, ttedb, dcps, main, all"
     exit 1
 fi

echo "🚀 Deploying $PROJECT from $BRANCH branch..."

 case $PROJECT in
     "ost")
         deploy_django_project "ost" "xeradb-ost"
         ;;
     "prct")
         deploy_django_project "prct" "xeradb-prct"
         ;;
     "cihrpt")
         deploy_django_project "cihrpt" "xeradb-cihrpt"
         ;;
     "nhmrcpt")
         deploy_django_project "nhmrcpt" "xeradb-nhmrcpt"
         ;;
     "nihrpt")
         deploy_django_project "nihrpt" "xeradb-nihrpt"
         ;;
     "nihpt")
         deploy_django_project "nihpt" "xeradb-nihpt"
         ;;
     "ttedb")
         deploy_django_project "ttedb" "xeradb-ttedb"
         ;;
     "dcps")
         deploy_django_project "dcps" "xeradb-dcps"
         ;;
     "main")
         cd /var/www/xeradb-main
         git pull origin $BRANCH
         npm install
         npm run build
         sudo systemctl reload nginx
         ;;
     "all")
         echo "🚀 Deploying all projects..."
         for proj in ost prct cihrpt nhmrcpt nihrpt nihpt ttedb dcps; do
             echo "Deploying $proj..."
             deploy_django_project "$proj" "xeradb-$proj"
         done
         ;;
     *)
         echo "Unknown project: $PROJECT"
         echo "Available projects: ost, prct, cihrpt, nhmrcpt, nihrpt, nihpt, ttedb, dcps, main, all"
         exit 1
         ;;
 esac

 function deploy_django_project() {
     local project=$1
     local service=$2
     
     cd /var/www/$project
     git pull origin $BRANCH
     source venv/bin/activate
     pip install -r requirements.txt
     python manage.py migrate
     python manage.py collectstatic --noinput
     sudo systemctl restart $service
 }

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
     "prct")
         sudo journalctl -u xeradb-prct -f
         ;;
     "cihrpt")
         sudo journalctl -u xeradb-cihrpt -f
         ;;
     "nhmrcpt")
         sudo journalctl -u xeradb-nhmrcpt -f
         ;;
     "nihrpt")
         sudo journalctl -u xeradb-nihrpt -f
         ;;
     "nihpt")
         sudo journalctl -u xeradb-nihpt -f
         ;;
     "ttedb")
         sudo journalctl -u xeradb-ttedb -f
         ;;
     "dcps")
         sudo journalctl -u xeradb-dcps -f
         ;;
     "nginx")
         sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
         ;;
     "system")
         sudo journalctl -f
         ;;
     "all")
         sudo journalctl -u xeradb-* -f
         ;;
     *)
         echo "Usage: $0 <ost|prct|cihrpt|nhmrcpt|nihrpt|nihpt|ttedb|dcps|nginx|system|all>"
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
             'prct': get_service_status('xeradb-prct'),
             'cihrpt': get_service_status('xeradb-cihrpt'),
             'nhmrcpt': get_service_status('xeradb-nhmrcpt'),
             'nihrpt': get_service_status('xeradb-nihrpt'),
             'nihpt': get_service_status('xeradb-nihpt'),
             'ttedb': get_service_status('xeradb-ttedb'),
             'dcps': get_service_status('xeradb-dcps'),
             'nginx': get_service_status('nginx'),
             'postgresql': get_service_status('postgresql')
         },
         'databases': {
             'ost_size': get_db_size('ost_production'),
             'prct_size': get_db_size('prct_production'),
             'cihrpt_size': get_db_size('cihrpt_production'),
             'nhmrcpt_size': get_db_size('nhmrcpt_production'),
             'nihrpt_size': get_db_size('nihrpt_production'),
             'nihpt_size': get_db_size('nihpt_production'),
             'ttedb_size': get_db_size('ttedb_production'),
             'dcps_size': get_db_size('dcps_production')
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
 pg_dump -h localhost -U prct_user prct_production > $BACKUP_DIR/prct_$DATE.sql
 pg_dump -h localhost -U cihrpt_user cihrpt_production > $BACKUP_DIR/cihrpt_$DATE.sql
 pg_dump -h localhost -U nhmrcpt_user nhmrcpt_production > $BACKUP_DIR/nhmrcpt_$DATE.sql
 pg_dump -h localhost -U nihrpt_user nihrpt_production > $BACKUP_DIR/nihrpt_$DATE.sql
 pg_dump -h localhost -U nihpt_user nihpt_production > $BACKUP_DIR/nihpt_$DATE.sql
 pg_dump -h localhost -U ttedb_user ttedb_production > $BACKUP_DIR/ttedb_$DATE.sql
 pg_dump -h localhost -U dcps_user dcps_production > $BACKUP_DIR/dcps_$DATE.sql
 
 # File backups
 for project in ost prct cihrpt nhmrcpt nihrpt nihpt ttedb dcps; do
     if [ -d "/var/www/$project/media" ]; then
         tar -czf $BACKUP_DIR/${project}_files_$DATE.tar.gz /var/www/$project/media
     fi
 done

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
| 3-5      | CAX31    | 8    | 16GB| 160GB   | $14.39       |
| 6-8      | **CAX41**| 16   | 32GB| 320GB   | **$28.79**   |
| 9+       | CAX51    | 32   | 64GB| 640GB   | $57.59       |

**🎯 Recommended for 8 Projects**: **CAX41** (16 vCPU, 32GB RAM, 320GB SSD)

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

### Phase 3: Additional Projects Setup (2-4 hours)
1. Set up PRCT (Post-Retraction Citation Tracker)
2. Configure funding trackers (CIHRPT, NHMRCPT, NIHRPT, NIHPT)
3. Deploy TTEdb (Target Trial Emulation Database) 
4. Set up DCPS (Dental Caries Population Studies)
5. Create Nginx virtual hosts and systemd services for each

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

## 🎨 Main Landing Page Structure

### Recommended xeradb.com Layout
```html
<!DOCTYPE html>
<html>
<head>
    <title>Xera DB - Open Science Research Platform</title>
</head>
<body>
    <header>
        <h1>🌟 Xera DB</h1>
        <p>Comprehensive Open Science Research Platform</p>
    </header>
    
    <main>
        <section id="transparency">
            <h2>📊 Research Transparency</h2>
            <div class="app-card">
                <h3>Open Science Tracker (OST)</h3>
                <p>Track transparency indicators in scientific publications</p>
                <a href="https://ost.xeradb.com">Launch OST →</a>
            </div>
        </section>
        
        <section id="retractions">
            <h2>🔄 Citation Analysis</h2>
            <div class="app-card">
                <h3>Post-Retraction Citation Tracker (PRCT)</h3>
                <p>Monitor citation patterns after paper retractions</p>
                <a href="https://prct.xeradb.com">Launch PRCT →</a>
            </div>
        </section>
        
        <section id="funding">
            <h2>💰 Research Funding Trackers</h2>
            <div class="app-grid">
                <div class="app-card">
                    <h3>CIHR Projects (Canada)</h3>
                    <a href="https://cihrpt.xeradb.com">Launch →</a>
                </div>
                <div class="app-card">
                    <h3>NHMRC Projects (Australia)</h3>
                    <a href="https://nhmrcpt.xeradb.com">Launch →</a>
                </div>
                <div class="app-card">
                    <h3>NIHR Projects (UK)</h3>
                    <a href="https://nihrpt.xeradb.com">Launch →</a>
                </div>
                <div class="app-card">
                    <h3>NIH Projects (USA)</h3>
                    <a href="https://nihpt.xeradb.com">Launch →</a>
                </div>
            </div>
        </section>
        
        <section id="clinical">
            <h2>🏥 Clinical Research</h2>
            <div class="app-card">
                <h3>Target Trial Emulation Database (TTEdb)</h3>
                <p>Clinical trial methodology and emulation studies</p>
                <a href="https://ttedb.xeradb.com">Launch TTEdb →</a>
            </div>
        </section>
        
        <section id="dental">
            <h2>🦷 Dental Research</h2>
            <div class="app-card">
                <h3>Dental Caries Population Studies (DCPS)</h3>
                <p>Population-based dental caries epidemiology</p>
                <a href="https://dcps.xeradb.com">Launch DCPS →</a>
            </div>
        </section>
    </main>
    
    <footer>
        <p>Powered by Open Science • <a href="https://docs.xeradb.com">Documentation</a></p>
    </footer>
</body>
</html>
```

---

**🌟 Result**: A comprehensive ecosystem of 8 specialized open science applications under the Xera DB brand, efficiently running on a single Hetzner VPS with proper isolation, automated deployment, monitoring, and backup strategies.

**📊 Total Capacity**: 
- 8 Django applications + 1 main site
- ~22,000 research papers + funding project data
- Professional subdomain structure
- Automated deployment and monitoring
- **Monthly Cost**: $28.79 (CAX41) for the entire ecosystem 