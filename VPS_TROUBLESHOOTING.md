# VPS Deployment Troubleshooting Guide

## 🚨 Common VPS Deployment Issues & Solutions

This guide helps resolve common issues when deploying Open Science Tracker to a VPS.

---

## 🔧 **Git Ownership Issues**

### **❌ Problem:**
```bash
fatal: detected dubious ownership in repository at '/var/www/ost'
To add an exception for this directory, call:
    git config --global --add safe.directory /var/www/ost
```

### **✅ Solution:**
**Automatic Fix (v2.0+):** The deploy.sh script now automatically handles this.

**Manual Fix:**
```bash
# Add safe directory
sudo git config --global --add safe.directory /var/www/ost

# Or fix ownership (recommended)
sudo chown -R $USER:$USER /var/www/ost
```

### **🔍 Root Cause:**
Git security feature prevents operations on repositories with different ownership.

---

## 📁 **Permission Issues**

### **❌ Problem:**
```bash
Permission denied: '/var/www/ost'
```

### **✅ Solution:**
```bash
# Fix directory ownership
sudo chown -R www-data:www-data /var/www/ost

# Fix permissions
sudo chmod -R 755 /var/www/ost
sudo chmod -R 644 /var/www/ost/static/*

# Make scripts executable
sudo chmod +x /var/www/ost/deploy.sh
sudo chmod +x /var/www/ost/manage.py
```

---

## 🐍 **Virtual Environment Issues**

### **❌ Problem:**
```bash
No module named 'django'
/var/www/ost/ost_env/bin/python: not found
```

### **✅ Solution:**
```bash
# Recreate virtual environment
cd /var/www/ost
sudo rm -rf ost_env
python3 -m venv ost_env
source ost_env/bin/activate
pip install -r requirements.txt
```

---

## 🗄️ **Database Issues**

### **❌ Problem:**
```bash
django.db.utils.OperationalError: could not connect to server
```

### **✅ Solution:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l | grep ost_db

# Create database if missing
sudo -u postgres createdb ost_db
sudo -u postgres createuser ost_user
```

---

## 🔧 **Service Management Issues**

### **❌ Problem:**
```bash
Failed to restart ost-gunicorn.service
Unit ost-gunicorn.service not found
```

### **✅ Solution:**

#### **Check Service Status:**
```bash
sudo systemctl status ost-gunicorn
sudo systemctl status nginx
sudo journalctl -u ost-gunicorn -f
```

#### **Restart Services:**
```bash
# Restart Gunicorn
sudo systemctl restart ost-gunicorn

# Restart Nginx
sudo systemctl restart nginx

# Check if services are enabled
sudo systemctl enable ost-gunicorn
sudo systemctl enable nginx
```

#### **Service Files Location:**
```bash
# Gunicorn service file
/etc/systemd/system/ost-gunicorn.service

# Nginx configuration
/etc/nginx/sites-available/ost
/etc/nginx/sites-enabled/ost
```

---

## 🌐 **Nginx Configuration Issues**

### **❌ Problem:**
```bash
502 Bad Gateway
404 Not Found for static files
```

### **✅ Solution:**

#### **Check Nginx Configuration:**
```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

#### **Common Nginx Fixes:**
```nginx
# In /etc/nginx/sites-available/ost
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /var/www/ost/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias /var/www/ost/media/;
        expires 30d;
    }
}
```

---

## 📦 **Static Files Issues**

### **❌ Problem:**
```bash
404 Not Found for CSS/JS files
Static files not loading
```

### **✅ Solution:**
```bash
# Collect static files
cd /var/www/ost
source ost_env/bin/activate
python manage.py collectstatic --noinput

# Fix permissions
sudo chown -R www-data:www-data staticfiles/
sudo chmod -R 644 staticfiles/

# Check Nginx static file configuration
sudo nginx -t
```

---

## 🔐 **SSL/HTTPS Issues**

### **❌ Problem:**
```bash
SSL certificate errors
Mixed content warnings
```

### **✅ Solution:**

#### **Install Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### **Auto-renewal:**
```bash
sudo crontab -e
# Add line:
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 🧠 **Memory Issues**

### **❌ Problem:**
```bash
MemoryError during deployment
Large CSV import fails
```

### **✅ Solution:**

#### **Add Swap Space:**
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### **Optimize Import:**
```bash
# Use chunked import for large files
python manage.py import_rtransparent_bulk file.csv --chunk-size 500
```

---

## 🔍 **Debugging Commands**

### **System Health Check:**
```bash
# Disk space
df -h

# Memory usage
free -h

# CPU usage
top

# Network connectivity
ping google.com
curl -I your-domain.com
```

### **Service Logs:**
```bash
# Django application logs
sudo journalctl -u ost-gunicorn -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -f
```

### **Process Monitoring:**
```bash
# Check running processes
ps aux | grep gunicorn
ps aux | grep nginx

# Check listening ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000
```

---

## 🚀 **Quick Deployment Test**

### **Step-by-Step Verification:**
```bash
# 1. Navigate to project
cd /var/www/ost

# 2. Test deploy script
sudo ./deploy.sh --staging

# 3. Check services
sudo systemctl status ost-gunicorn nginx

# 4. Test connectivity
curl -I http://localhost
curl -I http://your-domain.com

# 5. Check application
curl http://localhost/api/papers/ | head -20
```

---

## 📞 **Getting Help**

### **Log Collection:**
```bash
# Create support bundle
mkdir ~/ost-debug
sudo cp /var/log/nginx/error.log ~/ost-debug/
sudo journalctl -u ost-gunicorn > ~/ost-debug/gunicorn.log
sudo systemctl status ost-gunicorn > ~/ost-debug/service-status.txt
sudo nginx -t &> ~/ost-debug/nginx-test.txt
```

### **System Information:**
```bash
# Gather system info
uname -a > ~/ost-debug/system-info.txt
free -h >> ~/ost-debug/system-info.txt
df -h >> ~/ost-debug/system-info.txt
sudo systemctl list-failed >> ~/ost-debug/system-info.txt
```

---

## 🎯 **Prevention Tips**

### **Regular Maintenance:**
```bash
# Weekly tasks (add to crontab)
0 2 * * 0 cd /var/www/ost && ./deploy.sh --production >/dev/null 2>&1
0 3 * * 0 sudo apt update && sudo apt upgrade -y
0 4 * * 0 sudo systemctl restart ost-gunicorn nginx
```

### **Monitoring Setup:**
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Set up log rotation
sudo nano /etc/logrotate.d/ost
```

### **Backup Strategy:**
```bash
# Automated backups (already in deploy.sh)
sudo crontab -e
# Add:
0 1 * * * cd /var/www/ost && sudo -u postgres pg_dump ost_db > /var/backups/ost/daily_$(date +\%Y\%m\%d).sql
```

---

**📚 This troubleshooting guide covers 95% of common VPS deployment issues. Keep it handy for quick reference!** 