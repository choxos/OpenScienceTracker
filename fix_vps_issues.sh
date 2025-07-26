#!/bin/bash

# 🛠 VPS Issues Fix Script
# Resolves port conflicts, applies migrations, and restarts services

echo "🔧 OST VPS Issues Fix"
echo "===================="

# Step 1: Stop all conflicting services and processes
echo "🛑 Step 1: Stopping conflicting services..."

# Stop the OST service
sudo systemctl stop ost

# Kill any processes using port 8003
echo "🔍 Killing processes on port 8003..."
sudo fuser -k 8003/tcp 2>/dev/null || echo "No processes found on port 8003"

# Kill any background import processes
echo "🔍 Stopping background import processes..."
pkill -f "manual_process.py" 2>/dev/null || echo "No manual_process.py found"
pkill -f "process_transparency_files" 2>/dev/null || echo "No process_transparency_files found"
pkill -f "import_transparency" 2>/dev/null || echo "No import_transparency found"

# Wait a moment for processes to terminate
sleep 3

# Step 2: Apply pending migrations
echo "📊 Step 2: Applying database migrations..."
cd /var/www/ost
source ost_env/bin/activate

python manage.py migrate

if [ $? -ne 0 ]; then
    echo "❌ Migration failed! Check database connection."
    exit 1
fi

echo "✅ Migrations applied successfully"

# Step 3: Collect static files
echo "📦 Step 3: Collecting static files..."
python manage.py collectstatic --noinput

# Step 4: Test Django directly
echo "🧪 Step 4: Testing Django application..."
python manage.py check

if [ $? -ne 0 ]; then
    echo "❌ Django check failed!"
    exit 1
fi

echo "✅ Django check passed"

# Step 5: Verify port is free
echo "🔍 Step 5: Verifying port 8003 is free..."
if netstat -tlnp | grep :8003; then
    echo "❌ Port 8003 is still in use. Force killing..."
    sudo fuser -k 8003/tcp
    sleep 2
fi

echo "✅ Port 8003 is free"

# Step 6: Start the service
echo "🚀 Step 6: Starting OST service..."
sudo systemctl daemon-reload
sudo systemctl start ost

# Wait for service to start
sleep 3

# Step 7: Check service status
echo "📋 Step 7: Checking service status..."
sudo systemctl status ost --no-pager

# Step 8: Test the application
echo "🧪 Step 8: Testing application..."
echo "Testing localhost:8003..."
curl -I http://localhost:8003

echo ""
echo "Testing public domain..."
curl -I https://ost.xeradb.com

echo ""
echo "🎉 Fix complete! Check the output above for any remaining issues."
echo ""
echo "If still having issues, check logs with:"
echo "  sudo journalctl -u ost -f"
echo "  tail -f /var/www/ost/logs/ost.log" 