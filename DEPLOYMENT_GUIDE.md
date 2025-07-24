# 🚀 Open Science Tracker - Deployment Guide

This comprehensive guide covers how to deploy the Open Science Tracker (OST) application after making changes, whether for local development, staging, or production environments.

## 📋 Table of Contents

- [Quick Deployment Checklist](#quick-deployment-checklist)
- [Local Development Deployment](#local-development-deployment)
- [Production Deployment (VPS)](#production-deployment-vps)
- [Database Management](#database-management)
- [Static Files Management](#static-files-management)
- [Service Management](#service-management)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## ⚡ Quick Deployment Checklist

### For Local Development
```bash
# 1. Activate virtual environment
source ost_env/bin/activate  # Linux/Mac
# OR
ost_env\Scripts\activate     # Windows

# 2. Install/update dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Run development server
python manage.py runserver
```

### For Production (VPS)
```bash
# 1. Pull latest changes
git pull origin main

# 2. Activate virtual environment
source ost_env/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 7. Check status
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

## 🖥️ Local Development Deployment

### Initial Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/choxos/OpenScienceTracker.git
   cd OpenScienceTracker
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv ost_env
   source ost_env/bin/activate  # Linux/Mac
   # OR
   ost_env\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Create .env file (copy from .env.example if available)
   cp .env.example .env
   
   # Edit .env file with your local settings
   nano .env
   ```

5. **Database Setup**
   ```bash
   # Run initial migrations
   python manage.py migrate
   
   # Create superuser (optional)
   python manage.py createsuperuser
   
   # Load sample data (if available)
   python manage.py loaddata fixtures/sample_data.json
   ```

6. **Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Run Development Server**
   ```bash
   python manage.py runserver
   # Access at http://127.0.0.1:8000/
   ```

### After Making Changes

1. **Pull Latest Changes**
   ```bash
   git pull origin main
   ```

2. **Update Dependencies** (if requirements.txt changed)
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Migrations** (if models changed)
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Collect Static Files** (if CSS/JS changed)
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Restart Development Server**
   ```bash
   # Stop with Ctrl+C, then restart
   python manage.py runserver
   ```

---

## 🌐 Production Deployment (VPS)

### Prerequisites

- VPS with Ubuntu/Debian
- Python 3.8+
- PostgreSQL/MySQL (or SQLite for smaller deployments)
- Nginx
- Gunicorn
- Git

### Initial Production Setup

1. **System Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib
   ```

2. **Create User and Directory**
   ```bash
   sudo adduser ost
   sudo usermod -aG sudo ost
   su - ost
   mkdir /home/ost/apps
   cd /home/ost/apps
   ```

3. **Clone and Setup Application**
   ```bash
   git clone https://github.com/choxos/OpenScienceTracker.git
   cd OpenScienceTracker
   python3 -m venv ost_env
   source ost_env/bin/activate
   pip install -r requirements.txt
   ```

4. **Database Configuration**
   ```bash
   # For PostgreSQL
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb ost_production
   
   # Update settings.py or .env with production database settings
   ```

5. **Environment Variables**
   ```bash
   # Create production .env file
   nano .env
   ```
   ```env
   DEBUG=False
   SECRET_KEY=your-super-secret-key-here
   ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ip-address
   DATABASE_URL=postgresql://user:password@localhost/ost_production
   STATIC_ROOT=/home/ost/apps/OpenScienceTracker/staticfiles
   MEDIA_ROOT=/home/ost/apps/OpenScienceTracker/media
   ```

6. **Initial Deployment**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

### Gunicorn Configuration

1. **Create Gunicorn Service File**
   ```bash
   sudo nano /etc/systemd/system/gunicorn.service
   ```
   ```ini
   [Unit]
   Description=gunicorn daemon for Open Science Tracker
   After=network.target

   [Service]
   User=ost
   Group=www-data
   WorkingDirectory=/home/ost/apps/OpenScienceTracker
   ExecStart=/home/ost/apps/OpenScienceTracker/ost_env/bin/gunicorn \
             --access-logfile - \
             --workers 3 \
             --bind unix:/home/ost/apps/OpenScienceTracker/ost.sock \
             ost_web.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and Start Gunicorn**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable gunicorn
   sudo systemctl start gunicorn
   sudo systemctl status gunicorn
   ```

### Nginx Configuration

1. **Create Nginx Site Configuration**
   ```bash
   sudo nano /etc/nginx/sites-available/ost
   ```
   ```nginx
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /home/ost/apps/OpenScienceTracker;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }

       location /media/ {
           root /home/ost/apps/OpenScienceTracker;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/home/ost/apps/OpenScienceTracker/ost.sock;
       }
   }
   ```

2. **Enable Site and Restart Nginx**
   ```bash
   sudo ln -s /etc/nginx/sites-available/ost /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Production Deployment After Changes

1. **Connect to Server**
   ```bash
   ssh ost@your-server-ip
   cd /home/ost/apps/OpenScienceTracker
   ```

2. **Pull Latest Changes**
   ```bash
   git pull origin main
   ```

3. **Activate Virtual Environment**
   ```bash
   source ost_env/bin/activate
   ```

4. **Update Dependencies** (if requirements.txt changed)
   ```bash
   pip install -r requirements.txt
   ```

5. **Run Database Migrations** (if models changed)
   ```bash
   python manage.py migrate
   ```

6. **Collect Static Files** (if static files changed)
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Restart Services**
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

8. **Verify Deployment**
   ```bash
   sudo systemctl status gunicorn
   sudo systemctl status nginx
   curl -I http://your-domain.com
   ```

---

## 🗄️ Database Management

### Running Migrations

```bash
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# View migration status
python manage.py showmigrations

# View SQL for a migration (dry run)
python manage.py sqlmigrate tracker 0001
```

### Database Backup and Restore

```bash
# Backup (PostgreSQL)
pg_dump ost_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore (PostgreSQL)
psql ost_production < backup_20231201_120000.sql

# Backup (SQLite)
cp db.sqlite3 backup_$(date +%Y%m%d_%H%M%S).sqlite3
```

### Import Data Commands

```bash
# Set all papers to open access
python manage.py set_papers_open_access

# Import journal data
python manage.py import_from_osf

# Custom data imports (if applicable)
python manage.py import_medical_transparency_data
python manage.py import_dental_data
```

---

## 📁 Static Files Management

### Development
```bash
# Collect static files
python manage.py collectstatic --noinput

# Clear static files
python manage.py collectstatic --clear --noinput
```

### Production
```bash
# Collect with compression (if whitenoise is used)
python manage.py collectstatic --noinput

# Set proper permissions
sudo chown -R ost:www-data /home/ost/apps/OpenScienceTracker/staticfiles
sudo chmod -R 755 /home/ost/apps/OpenScienceTracker/staticfiles
```

---

## ⚙️ Service Management

### Gunicorn Commands
```bash
# Check status
sudo systemctl status gunicorn

# Start service
sudo systemctl start gunicorn

# Stop service
sudo systemctl stop gunicorn

# Restart service
sudo systemctl restart gunicorn

# Reload service (graceful restart)
sudo systemctl reload gunicorn

# View logs
sudo journalctl -u gunicorn

# Follow logs in real-time
sudo journalctl -u gunicorn -f
```

### Nginx Commands
```bash
# Check status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# Restart
sudo systemctl restart nginx

# Reload configuration
sudo systemctl reload nginx

# View logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔐 Environment Variables

### Required Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/database_name
# OR for SQLite
# DATABASE_URL=sqlite:///db.sqlite3

# Static and Media Files
STATIC_ROOT=/path/to/staticfiles
MEDIA_ROOT=/path/to/media

# Redis (if using caching)
REDIS_URL=redis://localhost:6379/0

# Email Configuration (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Third-party API Keys (if applicable)
EUROPEMC_API_KEY=your-api-key-here
```

### Generating Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000
sudo netstat -tlnp | grep :8000

# Kill process
sudo kill -9 <PID>

# Or use different port
python manage.py runserver 8001
```

#### 2. Permission Denied Errors
```bash
# Fix static files permissions
sudo chown -R ost:www-data /home/ost/apps/OpenScienceTracker/
sudo chmod -R 755 /home/ost/apps/OpenScienceTracker/

# Fix socket permissions
sudo chown ost:www-data /home/ost/apps/OpenScienceTracker/ost.sock
```

#### 3. Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
python manage.py dbshell

# Reset database (CAUTION: This deletes all data)
python manage.py flush
python manage.py migrate
```

#### 4. Static Files Not Loading
```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check Nginx configuration
sudo nginx -t

# Verify file permissions
ls -la /home/ost/apps/OpenScienceTracker/staticfiles/
```

#### 5. Gunicorn Not Starting
```bash
# Check Gunicorn directly
/home/ost/apps/OpenScienceTracker/ost_env/bin/gunicorn --bind 0.0.0.0:8000 ost_web.wsgi:application

# Check logs
sudo journalctl -u gunicorn -n 50

# Verify socket file
ls -la /home/ost/apps/OpenScienceTracker/ost.sock
```

### Log Files Locations

```bash
# Django logs (if configured)
tail -f logs/django.log

# Gunicorn logs
sudo journalctl -u gunicorn -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# System logs
sudo tail -f /var/log/syslog
```

---

## ↩️ Rollback Procedures

### Quick Rollback
```bash
# Rollback to previous commit
git log --oneline -n 10  # See recent commits
git checkout <previous-commit-hash>

# Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

### Database Rollback
```bash
# Rollback migrations (be careful!)
python manage.py migrate tracker 0001  # Rollback to specific migration

# Restore from backup
psql ost_production < backup_20231201_120000.sql
```

### Complete Rollback with Backup
```bash
# 1. Backup current state
pg_dump ost_production > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Checkout previous working version
git checkout <known-good-commit>

# 3. Restore database from backup
psql ost_production < backup_before_changes.sql

# 4. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

## 📝 Deployment Checklist

### Before Deployment
- [ ] Code is tested locally
- [ ] All tests pass
- [ ] Database migrations are created and tested
- [ ] Static files are updated
- [ ] Environment variables are configured
- [ ] Dependencies are updated in requirements.txt
- [ ] Security settings are reviewed

### During Deployment
- [ ] Backup current database
- [ ] Pull latest changes
- [ ] Update dependencies
- [ ] Run migrations
- [ ] Collect static files
- [ ] Restart services
- [ ] Test application functionality

### After Deployment
- [ ] Verify all pages load correctly
- [ ] Test critical functionality
- [ ] Check error logs
- [ ] Monitor performance
- [ ] Verify API endpoints
- [ ] Test search and filtering

---

## 🚨 Emergency Contacts and Resources

### Important Commands Quick Reference
```bash
# Emergency stop all services
sudo systemctl stop gunicorn nginx

# Emergency start all services
sudo systemctl start postgresql gunicorn nginx

# Check all service statuses
sudo systemctl status postgresql gunicorn nginx

# View recent logs
sudo journalctl -u gunicorn -n 100
sudo tail -f /var/log/nginx/error.log
```

### Useful Resources
- Django Documentation: https://docs.djangoproject.com/
- Gunicorn Documentation: https://gunicorn.org/
- Nginx Documentation: https://nginx.org/en/docs/
- PostgreSQL Documentation: https://www.postgresql.org/docs/

---

**⚠️ Always backup your database before major deployments!**

**📧 Contact: Ahmad Sofi-Mahmudi (ahmad.pub@gmail.com) for deployment support**

---

*Last Updated: 2025-01-20* 