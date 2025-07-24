# 🧪 **Quick Deployment Test Guide**

Test your deployment script before using it on your VPS.

## **🔍 Local Testing**

### **1. Test Script Syntax**
```bash
# Check for syntax errors
bash -n deploy.sh

# Test help function
./deploy.sh --help
```

### **2. Dry Run Simulation**
```bash
# Create a test environment simulation
mkdir -p /tmp/ost-test/{ost_env,static,media}
export PROJECT_DIR="/tmp/ost-test"

# Test individual functions (requires modification for testing)
# bash -c 'source deploy.sh; check_prerequisites'
```

## **📤 Transfer to VPS**

### **1. Copy Deployment Files**
```bash
# Upload deployment files to your VPS
scp deploy.sh your-user@your-vps-ip:/var/www/opensciencetracker/
scp deploy_commands.txt your-user@your-vps-ip:/var/www/opensciencetracker/
scp DEPLOYMENT_SETUP.md your-user@your-vps-ip:/var/www/opensciencetracker/
scp .deploy.conf your-user@your-vps-ip:/var/www/opensciencetracker/
```

### **2. Set Permissions on VPS**
```bash
# SSH into your VPS
ssh your-user@your-vps-ip

# Navigate to project directory
cd /var/www/opensciencetracker

# Make script executable
chmod +x deploy.sh

# Set proper ownership
sudo chown your-user:your-user deploy.sh deploy_commands.txt
```

### **3. Configure for Your Environment**
```bash
# Copy and edit configuration
cp .deploy.conf deploy.conf
nano deploy.conf  # Edit with your specific settings

# Edit the main script if needed
nano deploy.sh  # Adjust paths and service names
```

## **🚀 First Deployment Test**

### **1. Test Prerequisites**
```bash
# Check if all requirements are met
./deploy.sh --help
```

### **2. Safe Test Deployment**
```bash
# Test with staging environment (if configured)
./deploy.sh --staging --skip-backup

# Or test production with skip backup for first run
./deploy.sh --skip-backup --force
```

### **3. Monitor the Process**
```bash
# Watch deployment logs in another terminal
tail -f /var/log/ost_deploy.log
```

## **🔧 Common Issues & Solutions**

### **Permission Errors**
```bash
# Fix ownership issues
sudo chown -R www-data:www-data /var/www/opensciencetracker
```

### **Service Not Found**
```bash
# Check available services
systemctl list-units --type=service | grep -E "(nginx|gunicorn|ost)"

# Update service names in deploy.sh
nano deploy.sh  # Edit NGINX_SERVICE and GUNICORN_SERVICE
```

### **Database Backup Fails**
```bash
# Set up .pgpass for automated backups
echo "localhost:5432:ost_database:your_user:your_password" > ~/.pgpass
chmod 600 ~/.pgpass
```

## **✅ Success Checklist**

After successful deployment, verify:

- [ ] Website loads correctly
- [ ] Static files are served properly  
- [ ] Database migrations applied
- [ ] Services are running (`systemctl status nginx ost-gunicorn`)
- [ ] Logs show no errors (`tail /var/log/ost_deploy.log`)
- [ ] Admin panel accessible
- [ ] Search functionality works

## **📊 Performance Monitoring**

```bash
# Monitor resource usage during deployment
htop

# Check disk space
df -h

# Monitor deployment progress
tail -f /var/log/ost_deploy.log
```

## **🚨 Rollback if Needed**

If something goes wrong:

```bash
# Quick rollback
cd /var/www/opensciencetracker
sudo git reset --hard HEAD~1
sudo systemctl restart ost-gunicorn nginx
```

---

**🎯 Once tested successfully, you can use `./deploy.sh` for all future deployments!** 