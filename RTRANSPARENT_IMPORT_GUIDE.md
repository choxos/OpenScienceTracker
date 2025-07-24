# 🔬 **rtransparent Data Import Guide**

This guide explains how to efficiently import your large rtransparent medical transparency dataset (2.5GB, ~2.95M papers) into your Open Science Tracker database.

## 📊 **Dataset Overview**

### **Your CSV File Structure**
- **File**: `rtransparent_csvs/medicaltransparency_opendata.csv`
- **Size**: 2.5 GB
- **Records**: 2,953,887 papers
- **Date**: April 2024 (recent rtransparent analysis)

### **Available Fields**
✅ **Identifiers**: PMID, PMCID, DOI  
✅ **Paper Metadata**: Title, Authors, Journal, Publication Date  
✅ **Transparency Indicators**: COI, Funding, Registration, Open Data/Code  
✅ **Full Text**: COI text, funding text, registration statements  
✅ **Citations**: Citation counts from original analysis  

## 🚀 **Import Methods**

### **Method 1: Full Import (Recommended for Production)**

```bash
# Basic import (creates new papers, skips existing)
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv

# With journal creation
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --create-journals

# Update existing papers
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --update-existing --create-journals
```

### **Method 2: Test Import (Start Here)**

```bash
# Small test run (first 1000 records)
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --limit 1000 --create-journals

# Dry run to see what would happen
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --limit 100 --dry-run
```

### **Method 3: Chunked Import (For Large VPS)**

```bash
# Optimized for memory-constrained VPS (smaller chunks)
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --chunk-size 500 --batch-size 250 --create-journals

# Monitor memory usage
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --memory-limit 70 --create-journals
```

### **Method 4: Resume Import**

```bash
# Resume from specific row (if import was interrupted)
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --skip-rows 500000 --create-journals
```

## ⚙️ **Command Options**

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--chunk-size` | Records per chunk | 1000 | `--chunk-size 500` |
| `--batch-size` | Records per database batch | 500 | `--batch-size 250` |
| `--limit` | Maximum records to process | None | `--limit 10000` |
| `--skip-rows` | Skip first N rows | 0 | `--skip-rows 100000` |
| `--dry-run` | Test without saving | False | `--dry-run` |
| `--update-existing` | Update existing papers | False | `--update-existing` |
| `--create-journals` | Create missing journals | False | `--create-journals` |
| `--memory-limit` | Memory usage limit (%) | 80 | `--memory-limit 70` |

## 🔧 **VPS Setup Requirements**

### **1. Prerequisites**
```bash
# Install required Python packages
pip install pandas numpy tqdm psutil

# Check available disk space (need ~5GB free for processing)
df -h

# Check available RAM (recommend 4GB+ for full import)
free -h
```

### **2. Database Optimization**
```bash
# Connect to PostgreSQL
sudo -u postgres psql ost_database

-- Optimize for bulk imports
SET maintenance_work_mem = '2GB';
SET checkpoint_completion_target = 0.9;
SET wal_buffers = '16MB';
SET shared_buffers = '1GB';

-- Create indexes after import for better performance
```

### **3. File Transfer to VPS**
```bash
# Option 1: SCP Transfer (if you have good upload speed)
scp rtransparent_csvs/medicaltransparency_opendata.csv user@your-vps:/var/www/opensciencetracker/

# Option 2: Download directly on VPS (if file is hosted somewhere)
wget https://your-file-host.com/medicaltransparency_opendata.csv

# Option 3: Split and transfer (for slow connections)
split -l 100000 rtransparent_csvs/medicaltransparency_opendata.csv chunk_
# Transfer chunks separately, then concatenate on VPS
```

## 📈 **Performance Estimates**

### **Processing Speed Expectations**

| VPS Specs | Chunk Size | Expected Time | Records/Min |
|-----------|------------|---------------|-------------|
| 2GB RAM, 2 CPU | 500 | 8-12 hours | 4,000-6,000 |
| 4GB RAM, 4 CPU | 1000 | 4-6 hours | 8,000-12,000 |
| 8GB RAM, 8 CPU | 2000 | 2-3 hours | 15,000-20,000 |

### **Monitoring Progress**
The import includes a real-time progress bar showing:
- Records processed per second
- Estimated completion time
- Memory usage
- Created/Updated/Skipped counts

## 🔄 **Step-by-Step Import Process**

### **Step 1: Prepare VPS**
```bash
# Navigate to project directory
cd /var/www/opensciencetracker

# Activate virtual environment
source ost_env/bin/activate

# Ensure all migrations are applied
python manage.py migrate

# Check database connection
python manage.py dbshell
```

### **Step 2: Test Import**
```bash
# Start with a small test
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --limit 100 --dry-run --create-journals

# Run actual test import
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --limit 1000 --create-journals
```

### **Step 3: Monitor and Adjust**
```bash
# Check database size before
du -sh /var/lib/postgresql/

# Monitor during import
htop  # Check CPU and memory usage
iostat -x 1  # Check disk I/O

# Check import progress
tail -f /var/log/ost_deploy.log  # If logging is configured
```

### **Step 4: Full Import**
```bash
# Run full import in background with logging
nohup python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --create-journals > import.log 2>&1 &

# Monitor progress
tail -f import.log
```

### **Step 5: Verify Import**
```bash
# Check final paper count
python manage.py shell -c "from tracker.models import Paper; print(f'Total papers: {Paper.objects.count():,}')"

# Check transparency statistics
python manage.py shell -c "
from tracker.models import Paper
from django.db.models import Count
stats = Paper.objects.aggregate(
    total=Count('id'),
    with_coi=Count('id', filter={'is_coi_pred': True}),
    with_funding=Count('id', filter={'is_fund_pred': True}),
    with_data=Count('id', filter={'is_open_data': True}),
    with_code=Count('id', filter={'is_open_code': True})
)
print(f'Import Statistics:')
print(f'Total Papers: {stats[\"total\"]:,}')
print(f'COI Disclosure: {stats[\"with_coi\"]:,} ({stats[\"with_coi\"]/stats[\"total\"]*100:.1f}%)')
print(f'Funding Info: {stats[\"with_funding\"]:,} ({stats[\"with_funding\"]/stats[\"total\"]*100:.1f}%)')
print(f'Open Data: {stats[\"with_data\"]:,} ({stats[\"with_data\"]/stats[\"total\"]*100:.1f}%)')
print(f'Open Code: {stats[\"with_code\"]:,} ({stats[\"with_code\"]/stats[\"total\"]*100:.1f}%)')
"
```

## 🚨 **Troubleshooting**

### **Memory Issues**
```bash
# Reduce chunk size and batch size
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --chunk-size 200 --batch-size 100

# Lower memory limit trigger
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --memory-limit 60
```

### **Disk Space Issues**
```bash
# Check disk usage
df -h

# Clean up temporary files
python manage.py clearsessions
rm -f /tmp/*.csv

# Compress old log files
gzip /var/log/*.log
```

### **Database Lock Issues**
```bash
# If import fails with database locks
python manage.py dbshell

-- Check for blocking queries
SELECT pid, state, query FROM pg_stat_activity WHERE state = 'active';

-- Kill blocking processes if necessary
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';
```

### **Resume Interrupted Import**
```bash
# Check last imported paper ID
python manage.py shell -c "
from tracker.models import Paper
last_paper = Paper.objects.filter(transparency_processed=True).order_by('-created_at').first()
if last_paper:
    print(f'Last imported: {last_paper.pmid} at {last_paper.created_at}')
    # Estimate rows to skip based on pmid or creation time
"

# Resume from estimated position
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --skip-rows 1500000
```

## 📦 **Integration with Deployment**

### **Add to deploy_commands.txt**
```bash
# Add to deploy_commands.txt for automatic import during deployment
# import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --create-journals --update-existing
```

### **Manual Deployment Integration**
```bash
# Add import step to deployment script
./deploy.sh
python manage.py import_rtransparent_bulk rtransparent_csvs/medicaltransparency_opendata.csv --create-journals --update-existing
```

## 🎯 **Expected Results**

After successful import, your Open Science Tracker will have:

✅ **~2.95M research papers** with complete transparency analysis  
✅ **Rich metadata** including authors, journals, publication dates  
✅ **Comprehensive transparency indicators** from rtransparent analysis  
✅ **Full-text transparency statements** for manual review  
✅ **Citation data** for impact analysis  
✅ **Subject categorization** for field-specific analysis  

This will transform your OST into a comprehensive database of medical literature transparency! 🎉

---

**💡 Pro Tip**: Start with `--limit 1000` for testing, then run the full import during off-peak hours for best performance. 