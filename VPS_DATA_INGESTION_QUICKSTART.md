# VPS Data Ingestion - Quick Start Guide

## 🚀 **What You Need to Do Now**

### **1. Copy the Missing Files to Your VPS:**
```bash
# From your local machine, copy the new files to VPS
scp systemd/*.service xeradb@your-vps-ip:/tmp/
scp scripts/* xeradb@your-vps-ip:/var/www/ost/scripts/
scp requirements.txt xeradb@your-vps-ip:/var/www/ost/

# SSH into your VPS
ssh xeradb@your-vps-ip
```

### **2. Install Missing Dependencies:**
```bash
cd /var/www/ost
source ost_env/bin/activate
pip install -r requirements.txt
```

### **3. Install Systemd Services:**
```bash
# Copy service files to systemd directory
sudo cp /tmp/*.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable ost-web
sudo systemctl enable ost-data-monitor
```

### **4. Make Scripts Executable:**
```bash
chmod +x /var/www/ost/scripts/*.py
chmod +x /var/www/ost/scripts/*.sh
```

### **5. Create Required Directories:**
```bash
mkdir -p ~/epmc_monthly_data
mkdir -p ~/transparency_results
mkdir -p ~/logs
mkdir -p ~/backups
```

### **6. Start Services:**
```bash
sudo systemctl start ost-web
sudo systemctl start ost-data-monitor
```

## 📁 **How to Use the Data Ingestion System**

### **Automatic Processing:**
1. Drop EPMC files (like `epmc_db_2025_01.csv`) into: `~/epmc_monthly_data/`
2. Drop transparency files (like `transparency_2025_01.csv`) into: `~/transparency_results/`
3. The system automatically detects and processes them!

### **Manual Processing:**
```bash
cd /var/www/ost
source ost_env/bin/activate

# Process all files
python scripts/manual_process.py --all

# Process specific file
python scripts/manual_process.py --file ~/epmc_monthly_data/epmc_db_2025_01.csv

# Check status
python scripts/manual_process.py --status
```

### **Check System Status:**
```bash
# Check services
sudo systemctl status ost-web
sudo systemctl status ost-data-monitor

# Check logs
tail -f ~/logs/data_monitor.log
tail -f ~/logs/ost.log

# Check database
psql -h localhost -U ost_user -d ost_production -c "SELECT COUNT(*) FROM tracker_paper;"
```

## 🔧 **Commands to Check New Files**

Create this script to check for new files:

```bash
# Create check script
cat > ~/check_new_files.sh << 'EOF'
#!/bin/bash
echo "=== Checking for new data files ==="
echo "EPMC files in ~/epmc_monthly_data/:"
ls -la ~/epmc_monthly_data/*.csv 2>/dev/null | wc -l
echo "Transparency files in ~/transparency_results/:"
ls -la ~/transparency_results/*.csv 2>/dev/null | wc -l
echo "Last processed (check logs):"
tail -3 ~/logs/data_monitor.log
EOF

chmod +x ~/check_new_files.sh
```

Then run: `~/check_new_files.sh`

## 🎯 **Expected File Formats**

### **EPMC Files** (`epmc_db_YYYY_MM.csv`):
Should contain columns like: `id`, `source`, `title`, `authorString`, `journalTitle`, `pmid`, `pmcid`, `doi`, `isOpenAccess`, etc.

### **Transparency Files** (`transparency_YYYY_MM.csv`):
Should contain columns like: `pmid`, `pmcid`, `is_coi_pred`, `is_fund_pred`, `is_register_pred`, `is_open_data`, `is_open_code`, etc.

## 🚨 **Troubleshooting**

### **If services don't start:**
```bash
# Check service logs
sudo journalctl -u ost-web -f
sudo journalctl -u ost-data-monitor -f

# Restart services
sudo systemctl restart ost-web
sudo systemctl restart ost-data-monitor
```

### **If files aren't processing:**
```bash
# Check file monitor logs
tail -f ~/logs/data_monitor.log

# Manually trigger processing
cd /var/www/ost
source ost_env/bin/activate
python manage.py process_epmc_files
python manage.py process_transparency_files
```

### **Database Connection Issues:**
```bash
# Test database connection
psql -h localhost -U ost_user -d ost_production

# Check if PostgreSQL is running
sudo systemctl status postgresql
```

---

This system will automatically process your R-generated files as soon as you upload them to the VPS! 