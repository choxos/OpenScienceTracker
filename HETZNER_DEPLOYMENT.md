# 🚀 Hetzner VPS Deployment Guide for Open Science Tracker

Complete step-by-step guide to deploy Open Science Tracker on Ubuntu ARM-based VPS.

## 🏗️ Phase 1: VPS Setup & Initial Configuration

### Step 1: Create Hetzner VPS

1. Go to [Hetzner Cloud Console](https://console.hetzner-cloud.com/)
2. Create new project: **"OpenScienceTracker"**
3. Add server:
   - **Location**: Choose closest to you (Nuremberg, Helsinki, or Ashburn)
   - **Image**: Ubuntu 22.04 LTS
   - **Type**: ARM64 (CAX series)
   - **Size**: Recommended **CAX21** (4 vCPU, 8GB RAM, 80GB SSD) - $7.39/month
   - **SSH Key**: Add your public SSH key
   - **Name**: `ost-production`
4. Create server and note the IP address

### Step 2: Initial Server Security

```bash
# Connect to your VPS
ssh root@YOUR_SERVER_IP

# Update system
apt update && apt upgrade -y

# Create non-root user
adduser ost
usermod -aG sudo ost

# Copy SSH key to new user
cp -r /root/.ssh /home/ost/
chown -R ost:ost /home/ost/.ssh

# Configure SSH security
nano /etc/ssh/sshd_config
```

**Edit SSH config (`/etc/ssh/sshd_config`):**
```bash
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Port 22
```

```bash
# Restart SSH and switch to new user
systemctl restart ssh
exit

# Reconnect as new user
ssh ost@YOUR_SERVER_IP
```

## 🔧 Phase 2: Software Installation

### Step 3: Install Core Dependencies

```bash
# Update and install base packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    nginx postgresql postgresql-contrib git curl wget htop nano ufw \
    build-essential libpq-dev python3-dotenv

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp  
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### Step 4: PostgreSQL Setup

```bash
# Switch to postgres user and create database
sudo -u postgres psql
```

**In PostgreSQL prompt:**
```sql
CREATE DATABASE ost_production;
CREATE USER ost_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE ost_production TO ost_user;
ALTER USER ost_user CREATEDB;
\q
```

```bash
# Test connection
psql -h localhost -U ost_user -d ost_production
\q
```

## 📁 Phase 3: Application Deployment

### Step 5: Deploy Application Code

```bash
# Create application directory
sudo mkdir -p /var/www/ost
sudo chown ost:ost /var/www/ost
cd /var/www/ost

# Clone your repository
git clone https://github.com/choxos/OpenScienceTracker.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-dotenv
```

### Step 6: Environment Configuration

```bash
# Create environment file
nano .env
```

**Add to `.env` file:**
```bash
DEBUG=False
SECRET_KEY=your_super_secure_secret_key_here_generate_new_one
DATABASE_URL=postgresql://ost_user:your_secure_password_here@localhost:5432/ost_production
ALLOWED_HOSTS=your-domain.com,YOUR_SERVER_IP,localhost
STATIC_ROOT=/var/www/ost/staticfiles/
MEDIA_ROOT=/var/www/ost/media/
```

### Step 7: Django Production Settings

```bash
# Update settings for production
nano ost_web/production_settings.py
```

**Create `ost_web/production_settings.py`:**
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
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'your_secure_password_here'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static files
STATIC_ROOT = '/var/www/ost/staticfiles/'
STATIC_URL = '/static/'
MEDIA_ROOT = '/var/www/ost/media/'
MEDIA_URL = '/media/'

# Security settings
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

### Step 8: Database Migration & Data Import

```bash
# Activate virtual environment
source venv/bin/activate

# Set Django settings module
export DJANGO_SETTINGS_MODULE=ost_web.production_settings

# Create logs directory
mkdir -p logs

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Import research data (this will take several minutes)
python manage.py import_comprehensive_journals_bulk
python manage.py import_dental_papers_bulk

# Collect static files
python manage.py collectstatic --noinput

# Test the application
python manage.py runserver 0.0.0.0:8000
# Visit http://YOUR_SERVER_IP:8000 to test
# Press Ctrl+C to stop
```

## 🌐 Phase 4: Web Server Configuration

### Step 9: Gunicorn Setup

```bash
# Create Gunicorn configuration
nano /var/www/ost/gunicorn.conf.py
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
user = "ost"
group = "ost"
```

### Step 10: Systemd Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/ost.service
```

**Add to `ost.service`:**
```ini
[Unit]
Description=Open Science Tracker Gunicorn Application Server
After=network.target

[Service]
User=ost
Group=ost
WorkingDirectory=/var/www/ost
Environment="PATH=/var/www/ost/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=ost_web.production_settings"
ExecStart=/var/www/ost/venv/bin/gunicorn --config /var/www/ost/gunicorn.conf.py ost_web.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable ost
sudo systemctl start ost
sudo systemctl status ost
```

### Step 11: Nginx Configuration

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/ost
```

**Add to `ost` configuration:**
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

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
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/ost /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 Phase 5: SSL/HTTPS Setup (Optional but Recommended)

### Step 12: SSL Certificate with Let's Encrypt

```bash
# Install Certbot
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

## 🎯 Phase 6: Final Configuration & Testing

### Step 13: Performance Optimization

```bash
# Create backup script
nano /home/ost/backup.sh
```

**Add to `backup.sh`:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U ost_user ost_production > /home/ost/backups/ost_backup_$DATE.sql
find /home/ost/backups/ -name "ost_backup_*.sql" -mtime +7 -delete
```

```bash
# Make executable and create backups directory
chmod +x /home/ost/backup.sh
mkdir -p /home/ost/backups

# Add to crontab for daily backups
crontab -e
# Add this line:
# 0 2 * * * /home/ost/backup.sh
```

### Step 14: Monitoring Setup

```bash
# Install htop for system monitoring
sudo apt install htop

# Check application logs
sudo journalctl -u ost -f

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check application status
sudo systemctl status ost
sudo systemctl status nginx
sudo systemctl status postgresql
```

## 🎉 Deployment Complete!

Your Open Science Tracker is now deployed on Hetzner VPS!

### Access your application:
- **HTTP**: `http://YOUR_SERVER_IP` or `http://your-domain.com`
- **HTTPS**: `https://your-domain.com` (if SSL configured)
- **Admin**: `https://your-domain.com/admin/`

### Useful Commands:

```bash
# Restart application
sudo systemctl restart ost

# Update application
cd /var/www/ost
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart ost

# Check logs
sudo journalctl -u ost --since "1 hour ago"

# Database backup
pg_dump -h localhost -U ost_user ost_production > backup.sql

# Monitor resources
htop
df -h
free -h
```

## 🛠️ Troubleshooting

### Common Issues:

1. **Service won't start**: Check `sudo journalctl -u ost`
2. **Database connection error**: Verify PostgreSQL settings and password
3. **Permission errors**: Ensure ost user owns `/var/www/ost`
4. **Static files not loading**: Run `python manage.py collectstatic --noinput`
5. **Memory issues**: Reduce Gunicorn workers or upgrade VPS

### Support:
- Check Django logs: `/var/www/ost/logs/django.log`
- Check system logs: `sudo journalctl -xe`
- Monitor resources: `htop`, `df -h`, `free -h`

---

**Estimated Deployment Time**: 30-45 minutes  
**Monthly Cost**: ~$7.39 USD (CAX21 VPS)  
**Performance**: Handles thousands of users with 11K+ journals and 10K+ papers

🎯 **Your Open Science Tracker is now production-ready on Hetzner!** 