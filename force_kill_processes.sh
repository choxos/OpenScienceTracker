#!/bin/bash

# 🔥 Force Kill All OST Processes Script
# Aggressively stops all background processes and clears port conflicts

echo "🔥 FORCE KILL ALL OST PROCESSES"
echo "================================"

# Step 1: Stop the service immediately
echo "🛑 Stopping OST service..."
sudo systemctl stop ost
sudo systemctl disable ost  # Prevent auto-restart
sleep 2

# Step 2: Kill ALL python processes related to OST
echo "🔥 Killing ALL OST-related python processes..."
sudo pkill -f "gunicorn.*ost_web"
sudo pkill -f "python.*manage.py"
sudo pkill -f "manual_process"
sudo pkill -f "process_epmc"
sudo pkill -f "process_transparency"
sudo pkill -f "import_transparency"
sudo pkill -f "import_epmc"
sudo pkill -f "/var/www/ost"
sudo pkill -f "ost_env"

# Step 3: Kill everything on port 8003 (multiple times)
echo "🔥 Aggressively killing port 8003..."
for i in {1..5}; do
    echo "  Attempt $i/5..."
    sudo fuser -k 8003/tcp 2>/dev/null
    sudo lsof -ti:8003 | xargs sudo kill -9 2>/dev/null
    sleep 1
done

# Step 4: Check for any remaining processes
echo "🔍 Checking for remaining processes..."
if pgrep -f "ost_env\|manual_process\|process_epmc\|process_transparency"; then
    echo "🔥 Found remaining processes, force killing..."
    sudo pkill -9 -f "ost_env\|manual_process\|process_epmc\|process_transparency"
fi

# Step 5: Verify port is truly free
echo "🔍 Final port check..."
if netstat -tlnp | grep :8003; then
    echo "❌ Port still in use! Using nuclear option..."
    sudo netstat -tlnp | grep :8003 | awk '{print $7}' | cut -d'/' -f1 | xargs sudo kill -9
fi

sleep 3

# Step 6: Check if port is finally free
echo "✅ Port status:"
if netstat -tlnp | grep :8003; then
    echo "❌ Port 8003 is STILL in use:"
    netstat -tlnp | grep :8003
    echo ""
    echo "🚨 MANUAL INTERVENTION REQUIRED!"
    echo "Run: sudo reboot"
    exit 1
else
    echo "✅ Port 8003 is FREE!"
fi

# Step 7: Re-enable and start service
echo "🚀 Re-enabling and starting OST service..."
sudo systemctl enable ost
sudo systemctl daemon-reload
sudo systemctl start ost

sleep 3

# Step 8: Check final status
echo "📋 Final service status:"
sudo systemctl status ost --no-pager

echo ""
echo "🧪 Testing application..."
curl -I http://localhost:8003

echo ""
echo "🎉 Process complete!"
echo ""
echo "If still having issues, the server may need a reboot:"
echo "  sudo reboot" 