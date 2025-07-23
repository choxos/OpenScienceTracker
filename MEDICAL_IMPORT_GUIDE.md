# 🏥 Medical Data Import Guide with Progress Tracking

## Overview

The enhanced medical data import command now includes progress bars, memory monitoring, and resumption capabilities for importing the large 2.95M medical transparency records dataset.

## 🚀 Quick Start

### Basic Import (Full Dataset)
```bash
# Standard import with default settings
python manage.py import_medical_papers_bulk

# With custom batch size for better performance
python manage.py import_medical_papers_bulk --batch-size 1000
```

### Test Import (Limited Records)
```bash
# Import only first 10,000 records for testing
python manage.py import_medical_papers_bulk --max-records 10000

# Import only first 1,000 records with smaller batches
python manage.py import_medical_papers_bulk --max-records 1000 --batch-size 100
```

### Resume Import (If Interrupted)
```bash
# Skip first 500,000 records if import was interrupted
python manage.py import_medical_papers_bulk --skip-rows 500000

# Resume with smaller batch size to avoid memory issues
python manage.py import_medical_papers_bulk --skip-rows 500000 --batch-size 250
```

## 📊 Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--batch-size` | int | 500 | Records per batch (lower = less memory) |
| `--max-records` | int | None | Maximum records to import (for testing) |
| `--skip-rows` | int | 0 | Rows to skip at start (for resuming) |

## 🔍 Progress Monitoring

The command provides multiple types of progress tracking:

### 1. Overall Progress Bar
```
Processing medical papers: 45%|████▌     | 1,350,000/3,000,000 [12:34<15:22, 1,789.5 rows/s]
```

### 2. Chunk Processing
```
Chunk 27: 100%|██████████| 50,000/50,000 [02:15<00:00, 368.9 rows/s]
```

### 3. Memory Monitoring
```
💾 Memory usage: 342.5 MB
```

### 4. Import Statistics
```
✅ Medical bulk import completed!
📊 Total papers in database: 2,659,234
🏥 Medical papers imported: 2,650,000
📈 Records processed: 2,950,000
```

## 🗂️ File Locations

The command automatically searches for the medical dataset in these locations:
1. `rtransparent_csvs/medicaltransparency_opendata.csv`
2. `medicaltransparency_opendata.csv`
3. `medical_transparency_data.csv`

## 💾 Memory Optimization

### For VPS with Limited RAM (8GB or less):
```bash
# Use smaller batch sizes and chunk sizes
python manage.py import_medical_papers_bulk --batch-size 250
```

### For High-Memory Servers (16GB+):
```bash
# Use larger batch sizes for faster processing
python manage.py import_medical_papers_bulk --batch-size 1000
```

## 🔄 Resuming Interrupted Imports

If the import is killed or interrupted, you can resume from where it left off:

### Step 1: Check Current Progress
```bash
# Check how many papers are already imported
python manage.py shell -c "from tracker.models import Paper; print(f'Current papers: {Paper.objects.count():,}')"
```

### Step 2: Calculate Skip Rows
If you have 500,000 papers imported and were processing in chunks of 50,000:
```bash
# Skip approximately 500,000 rows to resume
python manage.py import_medical_papers_bulk --skip-rows 500000
```

### Step 3: Monitor Progress
Watch the progress bars and memory usage to ensure smooth completion.

## ⚠️ Production Deployment Notes

### Environment Detection
The command only runs in production environments:
- Railway environment (`RAILWAY_ENVIRONMENT` set)
- Production flag (`PRODUCTION=true`)
- Hetzner VPS (detected by `/var/www/ost` directory)

### Data Validation
- Automatically maps journals by title and ISSN
- Handles malformed dates and boolean values
- Truncates oversized fields to database limits
- Skips invalid records and continues processing

### Error Handling
- Continues processing if individual records fail
- Provides error summaries in progress bars
- Logs problematic records for later review

## 🎯 Performance Benchmarks

### Expected Processing Times (CAX21 VPS - 4 vCPU, 8GB RAM):
- **Full dataset (2.95M records)**: 45-90 minutes
- **Test dataset (10K records)**: 2-5 minutes
- **Processing rate**: 800-1,500 records/second

### Memory Usage:
- **Peak memory**: 300-500 MB
- **Chunk size**: 50,000 records
- **Garbage collection**: Automatic between chunks

## 🛠️ Troubleshooting

### Import Killed/Out of Memory
```bash
# Reduce batch size and retry
python manage.py import_medical_papers_bulk --batch-size 100 --skip-rows LAST_POSITION
```

### Slow Processing
```bash
# Increase batch size if you have more RAM
python manage.py import_medical_papers_bulk --batch-size 1000
```

### CSV File Not Found
```bash
# Check file locations
ls -la rtransparent_csvs/
ls -la *.csv
```

### Database Connection Issues
```bash
# Test database connection
python manage.py shell -c "from tracker.models import Journal; print(f'Journals: {Journal.objects.count()}')"
```

## 📈 Monitoring During Import

### Real-time Progress (in separate terminal):
```bash
# Watch paper count increase
watch -n 30 'python manage.py shell -c "from tracker.models import Paper; print(f\"Papers: {Paper.objects.count():,}\")"'
```

### System Resource Monitoring:
```bash
# Monitor CPU, memory, and disk usage
htop

# Watch memory usage
watch -n 5 'free -h'

# Monitor disk space
watch -n 30 'df -h'
```

## ✅ Validation After Import

### Data Quality Checks:
```bash
# Check total count
python manage.py shell -c "from tracker.models import Paper; print(f'Total papers: {Paper.objects.count():,}')"

# Check medical papers specifically
python manage.py shell -c "from tracker.models import Paper; print(f'Medical papers: {Paper.objects.filter(assessment_tool__icontains=\"rtransparent\").count():,}')"

# Check transparency indicators
python manage.py shell -c "from tracker.models import Paper; from django.db.models import Count; print(Paper.objects.aggregate(coi=Count('id', filter=models.Q(is_coi_pred=True)), funding=Count('id', filter=models.Q(is_fund_pred=True))))"
```

---

**💡 Pro Tip**: Start with a test import of 10,000 records to verify your setup before running the full import:

```bash
python manage.py import_medical_papers_bulk --max-records 10000 --batch-size 500
```

This guide ensures successful import of the large medical transparency dataset with full visibility into progress and system performance! 