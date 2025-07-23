# 🚀 Deploy OST to Hetzner VPS - Step by Step Guide

Deploy Open Science Tracker to your Hetzner VPS at `91.99.161.136` following the Xera DB ecosystem structure.

## 📋 Pre-Deployment Checklist

1. ✅ VPS is running (91.99.161.136)
2. ✅ SSH access as root
3. ✅ Domain `xeradb.com` pointed to 91.99.161.136 (if using custom domain)

## 🔧 Step 1: Initial Server Setup

```bash
# Connect to your VPS
ssh root@91.99.161.136

# Update system
apt update && apt upgrade -y

# Install core dependencies
apt install -y python3 python3-pip python3-venv python3-dev \
    nginx postgresql postgresql-contrib git curl wget htop nano ufw \
    build-essential libpq-dev python3-dotenv

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp  
ufw allow 443/tcp
ufw --force enable

# Create xeradb user (following ecosystem structure)
adduser xeradb
usermod -aG sudo xeradb

# Copy SSH key to new user
cp -r /root/.ssh /home/xeradb/
chown -R xeradb:xeradb /home/xeradb/.ssh

# Create Xera DB directory structure
mkdir -p /var/www/ost
mkdir -p /var/www/shared/{scripts,configs,ssl,logs}
mkdir -p /var/www/backups/{daily,weekly,monthly}
chown -R xeradb:xeradb /var/www/
```

## 🗄️ Step 2: PostgreSQL Database Setup

```bash
# Switch to postgres user and create database
sudo -u postgres psql

-- In PostgreSQL prompt, run these commands:
CREATE DATABASE ost_production;
CREATE USER ost_user WITH PASSWORD 'OSTSecure2025';
GRANT ALL PRIVILEGES ON DATABASE ost_production TO ost_user;
ALTER USER ost_user CREATEDB;
ALTER USER ost_user WITH SUPERUSER;
\q

# Fix PostgreSQL permissions (CRITICAL - prevents migration errors)
sudo -u postgres psql -d ost_production << 'EOF'
GRANT ALL ON SCHEMA public TO ost_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ost_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ost_user;
\q
EOF

# Test database connection
psql -h localhost -U ost_user -d ost_production -c "SELECT current_user, current_database();"
```

## 📁 Step 3: Deploy OST Application

```bash
# Switch to xeradb user
su - xeradb

# Navigate to OST directory
cd /var/www/ost

# Clone OST repository
git clone https://github.com/choxos/OpenScienceTracker.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-dotenv
```

## ⚙️ Step 4: Environment Configuration

```bash
# Create environment file
nano .env
```

**Create `.env` file with secure settings:**
```bash
# Generate a secure secret key and create .env file
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
cat > .env << EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
DATABASE_PASSWORD=OSTSecure2025
ALLOWED_HOSTS=ost.xeradb.com,91.99.161.136,localhost,xeradb.com
STATIC_ROOT=/var/www/ost/staticfiles/
MEDIA_ROOT=/var/www/ost/media/
EOF

# Verify .env file was created
cat .env
```

## 🐍 Step 5: Production Settings

```bash
# Create production settings
nano ost_web/production_settings.py
```

**Add to `ost_web/production_settings.py`:**
```python
from .settings import *
import os
from dotenv import load_dotenv

load_dotenv()

# Production settings
DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ost_production',
        'USER': 'ost_user',
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static files
STATIC_ROOT = '/var/www/ost/staticfiles/'
STATIC_URL = '/static/'
MEDIA_ROOT = '/var/www/ost/media/'
MEDIA_URL = '/media/'

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/www/ost/logs/django.log',
        },
    },
    'root': {
        'handlers': ['file'],
    },
}
```

## 🚀 Step 6: Initialize Application

```bash
# Create logs directory
mkdir -p logs

# Set Django settings module and bypass Railway environment check
export DJANGO_SETTINGS_MODULE=ost_web.production_settings
export RAILWAY_ENVIRONMENT=production

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Import research data (this will take several minutes)
echo "Starting comprehensive journals import..."
python manage.py import_comprehensive_journals_bulk

echo "Starting dental papers import..."
python manage.py import_dental_papers_bulk

# Collect static files
python manage.py collectstatic --noinput

# Test the application
python manage.py runserver 0.0.0.0:8000
# Visit http://91.99.161.136:8000 to test
# Press Ctrl+C to stop when confirmed working
```

## ⚙️ Step 7: Gunicorn Configuration

```bash
# Create Gunicorn configuration
nano gunicorn.conf.py
```

**Add to `gunicorn.conf.py`:**
```python
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
user = "xeradb"
group = "xeradb"
```

## 🔄 Step 8: Systemd Service

```bash
# Exit from xeradb user back to root
exit

# Create systemd service file
sudo nano /etc/systemd/system/xeradb-ost.service
```

**Add to `/etc/systemd/system/xeradb-ost.service`:**
```ini
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

```bash
# Enable and start the service
systemctl daemon-reload
systemctl enable xeradb-ost
systemctl start xeradb-ost
systemctl status xeradb-ost
```

## 🌐 Step 9: Nginx Configuration

```bash
# Create Nginx configuration
nano /etc/nginx/sites-available/ost
```

**Add to `/etc/nginx/sites-available/ost`:**
```nginx
server {
    listen 80;
    server_name ost.xeradb.com 91.99.161.136;

    client_max_body_size 100M;

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
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Add ecosystem headers
        add_header X-Powered-By "Xera-DB";
        add_header X-Project "OpenScienceTracker";
    }
}
```

```bash
# Enable the site
ln -s /etc/nginx/sites-available/ost /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## 🔒 Step 10: SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
apt install snapd
snap install core; snap refresh core
snap install --classic certbot
ln -s /snap/bin/certbot /usr/bin/certbot

# Get SSL certificate (if you have domain pointing to the server)
certbot --nginx -d ost.xeradb.com

# Or if using IP only, skip SSL for now
```

## ✅ Step 11: Final Testing & Verification

```bash
# Check all services are running
systemctl status xeradb-ost
systemctl status nginx
systemctl status postgresql

# Check application logs
journalctl -u xeradb-ost --since "5 minutes ago"

# Test the application
curl -I http://91.99.161.136/
# Should return HTTP 200 OK

# Check database has data
sudo -u xeradb psql -h localhost -U ost_user -d ost_production -c "SELECT COUNT(*) FROM tracker_journal;"
sudo -u xeradb psql -h localhost -U ost_user -d ost_production -c "SELECT COUNT(*) FROM tracker_paper;"
```

## 🎉 Deployment Complete!

Your Open Science Tracker is now deployed and accessible at:
- **HTTP**: `http://91.99.161.136`
- **HTTPS**: `https://ost.xeradb.com` (if SSL configured)
- **Admin**: `http://91.99.161.136/admin/`

### 🔧 Useful Commands for Maintenance:

```bash
# Restart OST application
sudo systemctl restart xeradb-ost

# Check logs
sudo journalctl -u xeradb-ost -f

# Update application
cd /var/www/ost
sudo -u xeradb git pull origin main
sudo -u xeradb bash -c "cd /var/www/ost && source venv/bin/activate && pip install -r requirements.txt"
sudo -u xeradb bash -c "cd /var/www/ost && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=ost_web.production_settings && python manage.py migrate"
sudo -u xeradb bash -c "cd /var/www/ost && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=ost_web.production_settings && python manage.py collectstatic --noinput"
sudo systemctl restart xeradb-ost

# Monitor resources
htop
df -h
free -h
```

## 🚨 Troubleshooting

### Common Issues:

1. **Migration fails with "permission denied for schema public"**: 
   - Run PostgreSQL permission fixes from Step 2
   - Grant superuser privileges: `sudo -u postgres psql -c "ALTER USER ost_user WITH SUPERUSER;"`

2. **Import commands skip with "Not in Railway environment"**:
   - Set environment variable: `export RAILWAY_ENVIRONMENT=production`

3. **Service won't start**: `sudo journalctl -u xeradb-ost`

4. **Database connection error**: Check password in `.env` file matches PostgreSQL user password

5. **Permission errors**: `sudo chown -R xeradb:xeradb /var/www/ost`

6. **502 Bad Gateway**: Check if gunicorn is running on port 8000: `sudo systemctl status xeradb-ost`

7. **Static files not loading**: Run `python manage.py collectstatic --noinput`

8. **Medical import fails**: Check file path `rtransparent_csvs/medicaltransparency_opendata.csv` exists

9. **Large dataset import timeout**: For medical data (2M+ records), consider running import in screen/tmux session

## 📊 Step 12: Import Medical Transparency Data (Optional)

**If you have medical transparency data to import:**

```bash
# Transfer medical data from local machine (run from local terminal)
scp -r rtransparent_csvs/ xeradb@91.99.161.136:/var/www/ost/

# On VPS: Create medical papers import command
cd /var/www/ost
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=ost_web.production_settings
export RAILWAY_ENVIRONMENT=production

# Create medical import command (handles different CSV structure)
cat > tracker/management/commands/import_medical_papers_bulk.py << 'EOF'
from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal
import pandas as pd
import os
from django.utils import timezone

class Command(BaseCommand):
    help = 'Bulk import medical transparency papers'

    def handle(self, *args, **options):
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🏥 Bulk importing medical transparency papers...'))
        
        existing_papers = Paper.objects.count()
        if existing_papers > 15000:
            self.stdout.write(self.style.WARNING(f'✅ Papers already imported ({existing_papers:,} found). Skipping.'))
            return
        
        try:
            df = pd.read_csv('rtransparent_csvs/medicaltransparency_opendata.csv')
            self.stdout.write(f"📄 Processing {len(df):,} medical transparency records")
            
            # Build journal mapping
            journal_map = {}
            journals = Journal.objects.all().values('id', 'title_abbreviation', 'title_full')
            for journal in journals:
                if journal['title_abbreviation']:
                    journal_map[journal['title_abbreviation'].lower()] = journal['id']
                if journal['title_full']:
                    journal_map[journal['title_full'].lower()] = journal['id']
            
            papers = []
            batch_size = 1000
            
            for idx, row in df.iterrows():
                if idx % 10000 == 0:
                    self.stdout.write(f"  Processing {idx:,}/{len(df):,} records...")
                
                # Find journal ID
                journal_title = str(row.get('journalTitle', '')).strip().lower()
                journal_id = journal_map.get(journal_title, min(journal_map.values()) if journal_map else 1)
                
                paper = Paper(
                    pmid=str(row.get('pmid', ''))[:20],
                    pmcid=str(row.get('pmcid', ''))[:20],
                    doi=str(row.get('doi', '')),
                    title=str(row.get('title', 'Unknown Title')),
                    author_string=str(row.get('authorString', '')),
                    journal_title=str(row.get('journalTitle', 'Unknown Journal')),
                    journal_issn=str(row.get('journalIssn', ''))[:9],
                    pub_year=self.extract_year(row.get('firstPublicationDate')),
                    first_publication_date=pd.to_datetime(row.get('firstPublicationDate'), errors='coerce'),
                    journal_volume=str(row.get('journalVolume', ''))[:20],
                    page_info=str(row.get('pageInfo', ''))[:50],
                    issue=str(row.get('issue', ''))[:20],
                    pub_type=str(row.get('type', ''))[:200],
                    scimago_publisher=str(row.get('scimago_publisher', '')),
                    is_coi_pred=str(row.get('is_coi_pred', '')).upper() == 'TRUE',
                    is_fund_pred=str(row.get('is_fund_pred', '')).upper() == 'TRUE',
                    is_register_pred=str(row.get('is_register_pred', '')).upper() == 'TRUE',
                    is_open_data=str(row.get('is_open_data', '')).upper() == 'TRUE',
                    is_open_code=str(row.get('is_open_code', '')).upper() == 'TRUE',
                    transparency_score=0,
                    transparency_score_pct=0.0,
                    assessment_tool='rtransparent',
                    ost_version='1.0',
                    assessment_date=timezone.now(),
                    journal_id=journal_id,
                )
                papers.append(paper)
                
                if len(papers) >= batch_size:
                    with transaction.atomic():
                        Paper.objects.bulk_create(papers, ignore_conflicts=True)
                    self.stdout.write(f'  ✅ Imported batch of {len(papers)} papers...')
                    papers = []
            
            if papers:
                with transaction.atomic():
                    Paper.objects.bulk_create(papers, ignore_conflicts=True)
                self.stdout.write(f'  ✅ Imported final batch of {len(papers)} papers')
            
            total_papers = Paper.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Medical import completed! Total papers: {total_papers:,}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
    
    def extract_year(self, date_str):
        if not date_str:
            return 2020
        try:
            if '-' in str(date_str):
                return int(str(date_str).split('-')[0])
            return int(float(date_str))
        except:
            return 2020
EOF

# Import medical papers (WARNING: This may take 30-60 minutes for large datasets)
echo "Starting medical papers import (this may take a while)..."
python manage.py import_medical_papers_bulk

# Check final database status
python manage.py shell -c "
from tracker.models import Journal, Paper
print(f'📚 Total Journals: {Journal.objects.count():,}')
print(f'📄 Total Papers: {Paper.objects.count():,}')
"
```

## 🔧 Step 13: Remove Superuser Privileges (Security)

```bash
# After all imports are complete, remove superuser privileges for security
sudo -u postgres psql -c "ALTER USER ost_user WITH NOSUPERUSER;"
```

### Next Steps:
1. Set up domain DNS (ost.xeradb.com → 91.99.161.136)
2. Configure SSL certificate with `certbot --nginx -d ost.xeradb.com`
3. Set up automated backups
4. Deploy additional Xera DB projects (PRCT, funding trackers, etc.)

🎯 **Your Open Science Tracker is now live and ready for research!** 