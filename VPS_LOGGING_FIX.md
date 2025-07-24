# VPS Logging Permission Fix Guide

## 🚨 **Issue:** Manual Process Fails After GitHub Pull

### **Error Message:**
```bash
PermissionError: [Errno 13] Permission denied: '/var/www/ost/ost.log'
ValueError: Unable to configure handler 'file'
```

### **Root Cause:**
After pulling updates from GitHub, Django's logging configuration can't write to the log file due to permission restrictions.

---

## ⚡ **Quick Fix Commands (Run on VPS)**

### **1. Immediate Fix - Set Permissions:**
```bash
# Navigate to project directory
cd /var/www/ost

# Create logs directory and set permissions
sudo mkdir -p logs
sudo mkdir -p /var/log/ost
sudo chown -R $USER:www-data logs/
sudo chown -R $USER:www-data /var/log/ost/
sudo chmod -R 775 logs/
sudo chmod -R 775 /var/log/ost/

# Fix project directory permissions
sudo chown -R $USER:www-data /var/www/ost
sudo chmod -R 755 /var/www/ost

# Create log files with proper permissions
touch logs/ost.log
sudo touch /var/log/ost/ost.log
sudo chown $USER:www-data logs/ost.log
sudo chown $USER:www-data /var/log/ost/ost.log
sudo chmod 664 logs/ost.log
sudo chmod 664 /var/log/ost/ost.log
```

### **2. Test the Fix:**
```bash
# Try running the manual process again
python scripts/manual_process.py --test

# If that works, run the full process
python scripts/manual_process.py --all
```

---

## 🔧 **Enhanced Logging Configuration**

The updated `settings.py` now includes **smart logging** that:

### **✅ Benefits:**
- **Gracefully handles permission errors**
- **Automatically tries multiple log locations:**
  1. `/var/log/ost/ost.log` (VPS standard)
  2. `/var/www/ost/logs/ost.log` (project directory)
  3. `/var/www/ost/ost.log` (project root)
  4. **Console only** (fallback)

### **🎯 Smart Features:**
- **Auto-creates log directories** when possible
- **Falls back to console logging** if file logging fails
- **Checks write permissions** before attempting file operations
- **Works in development and production** environments

---

## 📁 **Log File Locations (Priority Order)**

### **1. VPS System Logs (Preferred):**
```bash
/var/log/ost/ost.log
```
**Setup:**
```bash
sudo mkdir -p /var/log/ost
sudo chown $USER:www-data /var/log/ost
sudo chmod 775 /var/log/ost
```

### **2. Project Logs Directory:**
```bash
/var/www/ost/logs/ost.log
```
**Setup:**
```bash
mkdir -p /var/www/ost/logs
chmod 775 /var/www/ost/logs
```

### **3. Project Root (Legacy):**
```bash
/var/www/ost/ost.log
```

### **4. Console Only (Emergency Fallback):**
All logging goes to console/systemd journal.

---

## 🚀 **Automated Fix Script**

### **Create and Run Fix Script:**
```bash
# Create the fix script
cat > /var/www/ost/fix_logging.sh << 'EOF'
#!/bin/bash

echo "🔧 Fixing OST Logging Permissions..."

# Set project directory
PROJECT_DIR="/var/www/ost"
cd "$PROJECT_DIR"

# Create log directories
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/ost
mkdir -p logs

# Set ownership
echo "👤 Setting ownership..."
sudo chown -R $USER:www-data /var/log/ost
sudo chown -R $USER:www-data "$PROJECT_DIR/logs"
sudo chown -R $USER:www-data "$PROJECT_DIR"

# Set permissions
echo "🔐 Setting permissions..."
sudo chmod -R 775 /var/log/ost
chmod -R 775 logs
chmod -R 755 .

# Create log files
echo "📝 Creating log files..."
sudo touch /var/log/ost/ost.log
touch logs/ost.log
sudo chown $USER:www-data /var/log/ost/ost.log
chown $USER:www-data logs/ost.log
sudo chmod 664 /var/log/ost/ost.log
chmod 664 logs/ost.log

# Test Django startup
echo "🧪 Testing Django configuration..."
source ost_env/bin/activate
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()
print('✅ Django configuration successful!')
"

echo "✅ Logging permissions fixed!"
echo "📍 Log files available at:"
echo "   - /var/log/ost/ost.log (primary)"
echo "   - $PROJECT_DIR/logs/ost.log (backup)"
echo ""
echo "🚀 Ready to run manual_process.py!"
EOF

# Make executable and run
chmod +x fix_logging.sh
sudo ./fix_logging.sh
```

---

## 🔍 **Troubleshooting**

### **If the Script Fails:**

#### **Check Current User:**
```bash
whoami
groups
```

#### **Check Directory Permissions:**
```bash
ls -la /var/www/ost/
ls -la /var/log/
```

#### **Check Django Settings:**
```bash
cd /var/www/ost
source ost_env/bin/activate
python -c "
from ost_web.settings import LOGGING
print('Logging handlers:', list(LOGGING['handlers'].keys()))
print('Log file path:', LOGGING['handlers'].get('file', {}).get('filename', 'Console only'))
"
```

#### **Manual Permission Reset:**
```bash
# Nuclear option - reset all permissions
sudo chown -R xeradb:www-data /var/www/ost
sudo chmod -R 755 /var/www/ost
sudo chmod -R 775 /var/www/ost/logs
sudo chmod -R 775 /var/log/ost
```

---

## 📋 **Verification Steps**

### **1. Test Django Startup:**
```bash
cd /var/www/ost
source ost_env/bin/activate
python manage.py check
```

### **2. Test Logging:**
```bash
python -c "
import logging
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()
logger = logging.getLogger('tracker')
logger.info('Test log message')
print('Logging test successful!')
"
```

### **3. Run Manual Process:**
```bash
python scripts/manual_process.py --test
```

### **4. Check Log Files:**
```bash
# Check for log files
ls -la logs/
ls -la /var/log/ost/

# View recent logs
tail -f logs/ost.log
# OR
tail -f /var/log/ost/ost.log
```

---

## 💡 **Prevention Tips**

### **Add to Deployment Script:**
```bash
# Add to deploy.sh
echo "🔧 Setting up logging permissions..."
sudo mkdir -p /var/log/ost
mkdir -p logs
sudo chown -R \$USER:www-data /var/log/ost logs
sudo chmod -R 775 /var/log/ost logs
```

### **Systemd Service Permissions:**
```bash
# If using systemd, ensure proper user
sudo systemctl edit ost-gunicorn.service
```

Add:
```ini
[Service]
User=xeradb
Group=www-data
```

---

## ✅ **Success Indicators**

### **✅ Fixed When You See:**
```bash
# Manual process runs without errors
python scripts/manual_process.py --all

# Log files are being written
ls -la logs/ost.log /var/log/ost/ost.log

# Django starts without logging errors
python manage.py runserver
```

### **📈 Long-term Monitoring:**
```bash
# Add to crontab for log rotation
sudo crontab -e
# Add:
0 0 * * 0 /usr/sbin/logrotate /etc/logrotate.conf
```

**This fix ensures robust logging that works after any GitHub pull! 🚀** 