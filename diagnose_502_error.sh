#!/bin/bash

# 502 Bad Gateway Diagnostic Script for OST
# Diagnoses and fixes common issues after large dataset import

set -e

echo "🔍 OST 502 Bad Gateway Diagnostic Tool"
echo "======================================"

# Check if we're on the VPS
if [[ ! -d "/var/www/ost" ]]; then
    echo "❌ This script should be run on the VPS where OST is deployed"
    exit 1
fi

cd /var/www/ost

echo "📊 System Status Check..."
echo "------------------------"

# Memory check
echo "💾 Memory Usage:"
free -h
echo ""

# Disk space check
echo "💿 Disk Usage:"
df -h | grep -E "(Filesystem|/dev/)"
echo ""

# Process check
echo "🔄 Process Status:"
echo "Python processes:"
ps aux | grep python | grep -v grep || echo "No Python processes found"
echo ""

echo "Gunicorn processes:"
ps aux | grep gunicorn | grep -v grep || echo "No Gunicorn processes found"
echo ""

# Service status check
echo "🏗️  Service Status:"
echo "Gunicorn service:"
sudo systemctl status gunicorn --no-pager -l || echo "Gunicorn service not found or failed"
echo ""

echo "Nginx service:"
sudo systemctl status nginx --no-pager -l || echo "Nginx service not found or failed"
echo ""

# Database check
echo "🗃️  Database Status:"
if [[ -f "db.sqlite3" ]]; then
    db_size=$(du -h db.sqlite3 | cut -f1)
    echo "Database size: $db_size"
else
    echo "Database file not found"
fi

# Check if we can connect to database
echo "Database connectivity test:"
if python manage.py shell -c "from tracker.models import Paper; print(f'Papers in DB: {Paper.objects.count():,}')" 2>/dev/null; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
fi
echo ""

# Log file check
echo "📋 Recent Error Logs:"
echo "Gunicorn logs (last 20 lines):"
if [[ -f "/var/log/gunicorn/error.log" ]]; then
    sudo tail -20 /var/log/gunicorn/error.log
elif [[ -f "/var/log/ost/gunicorn.log" ]]; then
    sudo tail -20 /var/log/ost/gunicorn.log
else
    echo "Gunicorn log file not found"
fi
echo ""

echo "Nginx error logs (last 10 lines):"
sudo tail -10 /var/log/nginx/error.log 2>/dev/null || echo "Nginx error log not accessible"
echo ""

echo "Django logs (if available):"
if [[ -f "/var/log/ost/ost.log" ]]; then
    tail -10 /var/log/ost/ost.log
elif [[ -f "logs/ost.log" ]]; then
    tail -10 logs/ost.log
else
    echo "Django log file not found"
fi
echo ""

# Check configuration files
echo "⚙️  Configuration Check:"
echo "Gunicorn configuration:"
if [[ -f "/etc/systemd/system/gunicorn.service" ]]; then
    echo "Service file exists"
    grep -E "(WorkingDirectory|ExecStart|User)" /etc/systemd/system/gunicorn.service
else
    echo "Gunicorn service file not found"
fi
echo ""

# Port check
echo "🌐 Port Status:"
echo "Port 8000 (Gunicorn):"
sudo netstat -tlnp | grep :8000 || echo "Port 8000 not listening"
echo ""

echo "Port 80/443 (Nginx):"
sudo netstat -tlnp | grep -E ":(80|443)" || echo "Nginx ports not listening"
echo ""

echo "🎯 Diagnosis Complete"
echo "==================="

# Provide recommendations based on findings
echo ""
echo "💡 Recommended Actions:"
echo "1. Check if Gunicorn crashed (restart if needed)"
echo "2. Verify memory usage (may need to increase worker memory)"
echo "3. Check database connectivity"
echo "4. Review error logs for specific issues"
echo "5. Consider optimizing settings for large dataset"
echo ""

echo "🛠️  Quick Fix Commands:"
echo "sudo systemctl restart gunicorn"
echo "sudo systemctl restart nginx"
echo "sudo ./fix_502_error.sh  # (if available)" 