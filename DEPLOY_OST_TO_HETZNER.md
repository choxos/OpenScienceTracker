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
CREATE USER ost_user WITH PASSWORD 'your_secure_password_here_change_this';
GRANT ALL PRIVILEGES ON DATABASE ost_production TO ost_user;
ALTER USER ost_user CREATEDB;
\q

# Test database connection
psql -h localhost -U ost_user -d ost_production
-- Type some test command like: \dt
\q
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

**Add to `.env` file (replace the password with your actual secure password):**
```bash
DEBUG=False
SECRET_KEY=your_super_secure_secret_key_here_generate_new_one
DATABASE_PASSWORD=your_secure_password_here_change_this
ALLOWED_HOSTS=ost.xeradb.com,91.99.161.136,localhost,xeradb.com
STATIC_ROOT=/var/www/ost/staticfiles/
MEDIA_ROOT=/var/www/ost/media/
```

```bash
# Generate a secure secret key
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copy this output and replace the SECRET_KEY in .env file
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

# Set Django settings module
export DJANGO_SETTINGS_MODULE=ost_web.production_settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Import research data (this will take several minutes)
echo "Starting journal import..."
python manage.py import_comprehensive_journals_bulk

echo "Starting papers import..."
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
sudo -u xeradb /var/www/ost/venv/bin/pip install -r requirements.txt
sudo -u xeradb /var/www/ost/venv/bin/python manage.py migrate
sudo -u xeradb /var/www/ost/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart xeradb-ost

# Monitor resources
htop
df -h
free -h
```

## 🚨 Troubleshooting

### Common Issues:

1. **Service won't start**: `sudo journalctl -u xeradb-ost`
2. **Database connection error**: Check password in `.env` file
3. **Permission errors**: `sudo chown -R xeradb:xeradb /var/www/ost`
4. **502 Bad Gateway**: Check if gunicorn is running on port 8000
5. **Static files not loading**: Run `python manage.py collectstatic --noinput`

### Next Steps:
1. Set up domain DNS (ost.xeradb.com → 91.99.161.136)
2. Configure SSL certificate
3. Set up automated backups
4. Deploy additional Xera DB projects

🎯 **Your Open Science Tracker is now live and ready for research!** 