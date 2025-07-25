# 🔒 QUICK FIX - Database Lock Issue (502 Bad Gateway)

## 🚨 **Problem Identified**
Your import process is stuck and has locked the database, preventing Django from running and causing the 502 Bad Gateway error.

## ⚡ **IMMEDIATE SOLUTION - Run on VPS**

### **Step 1: Stop All Services**
```bash
cd /var/www/ost
sudo systemctl stop gunicorn
sudo systemctl stop nginx
```

### **Step 2: Kill Stuck Import Processes**
```bash
# Kill any stuck manual_process.py
pkill -f "manual_process.py"

# Kill any other stuck import processes
pkill -f "python scripts"
pkill -f "import_"

# Verify no Python processes are stuck
ps aux | grep python
```

### **Step 3: Unlock SQLite Database**
```bash
# Check for lock files
ls -la db.sqlite3*

# Remove SQLite lock files if they exist
rm -f db.sqlite3-wal db.sqlite3-shm

# Test database unlock
sqlite3 db.sqlite3 "BEGIN IMMEDIATE; ROLLBACK;"

# If that works, optimize database
sqlite3 db.sqlite3 "VACUUM; ANALYZE;"
```

### **Step 4: Test Django Database Access**
```bash
source ost_env/bin/activate
python manage.py shell -c "
from tracker.models import Paper
try:
    count = Paper.objects.count()
    print(f'✅ Database working: {count:,} papers')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

### **Step 5: Restart Services**
```bash
# Start Gunicorn with increased timeout for large database
sudo systemctl start gunicorn

# Start Nginx
sudo systemctl start nginx

# Check status
sudo systemctl status gunicorn
sudo systemctl status nginx
```

### **Step 6: Test Website**
```bash
# Test local Django
curl -I http://127.0.0.1:8000

# Test through Nginx
curl -I http://localhost

# Should return 200 or 301/302, not 502
```

## 🔧 **If Still Not Working**

### **Alternative Method - Force Unlock**
```bash
# If database is still locked, try this stronger approach:
sudo systemctl stop gunicorn
sudo fuser -k db.sqlite3  # Kill any processes using the database file
rm -f db.sqlite3-wal db.sqlite3-shm
sqlite3 db.sqlite3 ".timeout 30" "VACUUM;"
sudo systemctl start gunicorn
```

### **Check Logs for Details**
```bash
# Check Gunicorn logs
sudo journalctl -u gunicorn -f

# Check Django errors
python manage.py check --deploy

# Check if database is really unlocked
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM tracker_paper LIMIT 1;"
```

## 🎯 **Root Cause**
Your `manual_process.py --all` command got stuck or was interrupted, leaving the SQLite database in a locked state. This prevented Django/Gunicorn from accessing the database, causing the 502 error.

## 🛡️ **Prevention for Future Imports**

### **Safe Import Process**
```bash
# 1. Always stop services before large imports
sudo systemctl stop gunicorn

# 2. Use batch processing
python scripts/manual_process.py --batch-size 1000

# 3. Monitor progress (don't interrupt)
tail -f /var/log/ost/ost.log

# 4. Restart services after completion
sudo systemctl start gunicorn
```

### **Alternative: Use Optimized Import Script**
```bash
# Use the new optimized script instead
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv --batch-size 500 --limit 10000  # Test first
```

## ✅ **Expected Result**
After following these steps, your website should respond normally and the 502 Bad Gateway error should be resolved.

---

**🚀 This should fix your 502 error within 2-3 minutes!** 