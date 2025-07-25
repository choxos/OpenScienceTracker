# 🐘 POSTGRESQL 502 Fix - Database Lock Issue

## 🚨 **IMMEDIATE SOLUTION FOR POSTGRESQL**

Your `manual_process.py --all` got stuck and is holding PostgreSQL connections/locks, causing the 502 Bad Gateway error.

## ⚡ **QUICK FIX - Run on VPS:**

### **Step 1: Stop Services & Kill Stuck Processes**
```bash
cd /var/www/ost

# Stop services
sudo systemctl stop gunicorn nginx

# Kill stuck import processes
pkill -f "manual_process.py"
pkill -f "python scripts"

# Wait for processes to die
sleep 5
```

### **Step 2: Check PostgreSQL Status**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# If not running, start it
sudo systemctl start postgresql
```

### **Step 3: Kill Long-Running Database Connections**
```bash
# Get your database name from Django settings
source ost_env/bin/activate
DB_NAME=$(python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])")

echo "Database: $DB_NAME"

# Check for active connections
sudo -u postgres psql -d "$DB_NAME" -c "
SELECT pid, usename, application_name, state, query_start, now() - query_start AS duration 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' AND state != 'idle'
ORDER BY query_start;
"

# Kill long-running queries (>5 minutes)
sudo -u postgres psql -d "$DB_NAME" -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME' 
AND state != 'idle' 
AND now() - query_start > interval '5 minutes';
"
```

### **Step 4: Optimize Database**
```bash
# Run PostgreSQL optimization
sudo -u postgres psql -d "$DB_NAME" -c "VACUUM ANALYZE;"
```

### **Step 5: Test Django Database Access**
```bash
# Test Django can connect to database
python manage.py shell -c "
from tracker.models import Paper
try:
    count = Paper.objects.count()
    print(f'✅ Database working: {count:,} papers')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

### **Step 6: Restart Services**
```bash
# Start Gunicorn with PostgreSQL optimizations
sudo systemctl start gunicorn

# Check status
sudo systemctl status gunicorn

# Start Nginx
sudo systemctl start nginx

# Check website
curl -I http://localhost
```

## 🔧 **If Still Getting 502 Error:**

### **Check Gunicorn Logs**
```bash
sudo journalctl -u gunicorn -f
```

### **Check PostgreSQL Logs**
```bash
sudo journalctl -u postgresql -f
```

### **Manual Database Connection Test**
```bash
# Test direct PostgreSQL connection
sudo -u postgres psql -d "$DB_NAME" -c "SELECT COUNT(*) FROM tracker_paper LIMIT 1;"
```

## 🛠️ **Use Automated Script**
```bash
cd /var/www/ost
git pull origin main
chmod +x fix_postgres_lock.sh
./fix_postgres_lock.sh
```

## 🎯 **Root Cause (PostgreSQL-specific)**
Unlike SQLite, PostgreSQL uses session-based locks. Your stuck `manual_process.py` is holding database connections that prevent Django/Gunicorn from accessing the database properly.

## 🛡️ **Prevention for Future Large Imports**
```bash
# 1. Always stop Gunicorn before large imports
sudo systemctl stop gunicorn

# 2. Monitor PostgreSQL connections during import
watch -n 10 'sudo -u postgres psql -d YOUR_DB_NAME -c "SELECT count(*) FROM pg_stat_activity;"'

# 3. Use the optimized import script instead
python manage.py import_rtransparent_medical file.csv --batch-size 500

# 4. Restart services after import
sudo systemctl start gunicorn
```

## ✅ **Expected Result**
Your 502 Bad Gateway error should be resolved within 2-3 minutes after running these PostgreSQL-specific commands.

---

**🚀 PostgreSQL-specific solution for your VPS!** 