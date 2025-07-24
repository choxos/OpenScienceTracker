# 🚀 **Automated Deployment Setup Guide**

This guide will help you configure the `deploy.sh` script for your VPS environment.

## **📋 Prerequisites**

### **1. Server Requirements**
- Ubuntu/Debian VPS with sudo access
- Python 3.8+ installed
- PostgreSQL database
- Nginx web server
- Git installed and configured

### **2. Project Structure on VPS**
```
/var/www/opensciencetracker/        # Main project directory
├── ost_env/                        # Virtual environment
├── manage.py                       # Django management script
├── requirements.txt                # Python dependencies
├── ost_web/                       # Django project
└── static/                        # Static files
```

## **⚙️ Configuration Steps**

### **1. Edit Deploy Script Configuration**
Open `deploy.sh` and adjust these variables for your server:

```bash
# Project Configuration
PROJECT_DIR="/var/www/opensciencetracker"     # Your project path
VENV_DIR="$PROJECT_DIR/ost_env"               # Virtual environment path
BACKUP_DIR="/var/backups/ost"                # Backup storage location
LOG_FILE="/var/log/ost_deploy.log"           # Deployment log file

# Service Configuration
NGINX_SERVICE="nginx"                         # Nginx service name
GUNICORN_SERVICE="ost-gunicorn"              # Your Gunicorn service name
SUPERVISOR_PROGRAM="ost"                      # Supervisor program name (if using)

# Database Configuration  
DATABASE_NAME="ost_database"                  # Your PostgreSQL database name
```

### **2. Create Gunicorn Service** (if not already configured)
Create `/etc/systemd/system/ost-gunicorn.service`:

```ini
[Unit]
Description=OST Gunicorn Application Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/opensciencetracker
Environment="PATH=/var/www/opensciencetracker/ost_env/bin"
ExecStart=/var/www/opensciencetracker/ost_env/bin/gunicorn \
          --workers 3 \
          --bind unix:/var/www/opensciencetracker/ost.sock \
          ost_web.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ost-gunicorn
sudo systemctl start ost-gunicorn
```

### **3. Configure Nginx** (if not already configured)
Create `/etc/nginx/sites-available/opensciencetracker`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/opensciencetracker;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /var/www/opensciencetracker;
        expires 7d;
    }
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/opensciencetracker/ost.sock;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/opensciencetracker /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### **4. Set Up Database Backup** (Optional)
Ensure PostgreSQL can create backups without password prompt:

```bash
# Create .pgpass file for automated backups
echo "localhost:5432:ost_database:your_db_user:your_db_password" > ~/.pgpass
chmod 600 ~/.pgpass
```

### **5. Create Backup Directory**
```bash
sudo mkdir -p /var/backups/ost
sudo chown $(whoami):$(whoami) /var/backups/ost
```

### **6. Set Up Log File**
```bash
sudo touch /var/log/ost_deploy.log
sudo chmod 644 /var/log/ost_deploy.log
sudo chown $(whoami):$(whoami) /var/log/ost_deploy.log
```

## **🎯 Usage Examples**

### **Basic Deployment**
```bash
./deploy.sh
```

### **Staging Deployment**
```bash
./deploy.sh --staging
```

### **Force Deployment** (even if no git changes)
```bash
./deploy.sh --force
```

### **Skip Backup** (faster deployment)
```bash
./deploy.sh --skip-backup
```

### **Deploy Specific Branch**
```bash
./deploy.sh --branch develop
```

### **Combined Options**
```bash
./deploy.sh --staging --skip-backup --force
```

## **📝 Custom Management Commands**

Edit `deploy_commands.txt` to add custom Django management commands that should run during deployment:

```txt
# Uncomment commands you want to run:
clearsessions
# update_index
# compress
# clear_cache
```

## **🔍 Monitoring & Troubleshooting**

### **Check Deployment Logs**
```bash
tail -f /var/log/ost_deploy.log
```

### **Check Service Status**
```bash
sudo systemctl status ost-gunicorn
sudo systemctl status nginx
```

### **Manual Service Restart**
```bash
sudo systemctl restart ost-gunicorn
sudo systemctl restart nginx
```

### **Check Django**
```bash
cd /var/www/opensciencetracker
source ost_env/bin/activate
python manage.py check --deploy
```

## **🔐 Security Considerations**

1. **File Permissions**: Script automatically sets secure permissions
2. **Environment Variables**: Store sensitive data in `.env` file (not in Git)
3. **Database Backups**: Stored in `/var/backups/ost` with restricted access
4. **Log Files**: Monitor `/var/log/ost_deploy.log` for any issues

## **⚡ Performance Tips**

1. **Use `--skip-backup`** for faster deployments when backup isn't critical
2. **Deploy during low-traffic periods** to minimize user impact
3. **Monitor resource usage** during deployment on smaller VPS instances
4. **Use staging environment** for testing major changes

## **🚨 Emergency Rollback**

If deployment fails, you can quickly rollback:

```bash
# Go to project directory
cd /var/www/opensciencetracker

# Rollback to previous commit
sudo git reset --hard HEAD~1

# Restart services
sudo systemctl restart ost-gunicorn nginx

# Restore database backup if needed
sudo -u postgres psql ost_database < /var/backups/ost/latest_backup.sql
```

## **📞 Support**

If you encounter issues:
1. Check deployment logs: `/var/log/ost_deploy.log`
2. Verify service status: `systemctl status ost-gunicorn nginx`
3. Test Django configuration: `python manage.py check --deploy`
4. Check server resources: `htop`, `df -h`

---

**🎉 Your automated deployment is now ready! Run `./deploy.sh` to deploy your latest changes.** 