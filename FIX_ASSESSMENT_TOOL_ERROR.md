# Fix Assessment Tool Import Error - VPS Guide

## 🚨 **Problem:**
```
❌ Import failed: Cannot resolve keyword 'assessment_tool' into field.
django.core.exceptions.FieldError: Cannot resolve keyword 'assessment_tool' into field.
```

## 🔍 **Root Cause:**
The import command is trying to filter/set `assessment_tool='rtransparent'`, but this field doesn't exist in the database yet.

## ✅ **Solution Applied:**
Added `assessment_tool` field to track which tool was used for transparency assessment.

---

## 🚀 **VPS Fix Steps**

### **Step 1: Pull Latest Changes**
```bash
cd /var/www/ost
git pull origin main
```

### **Step 2: Apply Database Migration**
```bash
source ost_env/bin/activate
python manage.py migrate

# You should see:
# Running migrations:
#   Applying tracker.0004_add_assessment_tool_field... OK
```

### **Step 3: Verify Field Added**
```bash
# Test the field exists
python manage.py shell -c "
from tracker.models import Paper
field_names = [f.name for f in Paper._meta.get_fields()]
if 'assessment_tool' in field_names:
    print('✅ assessment_tool field added successfully')
else:
    print('❌ assessment_tool field missing')
"
```

### **Step 4: Resume Import**
```bash
# Now your import should work
python manage.py import_medical_papers_bulk [your-csv-file]
```

---

## 📋 **What Was Added**

### **New Field in Paper Model:**
```python
assessment_tool = models.CharField(
    max_length=50, 
    default='rtransparent', 
    db_index=True,
    help_text="Tool used for transparency assessment (e.g., rtransparent, manual)"
)
```

### **Features:**
- ✅ **Default value**: `'rtransparent'` for new records
- ✅ **Database index**: For efficient filtering
- ✅ **API serialization**: Available in REST API responses
- ✅ **Admin interface**: Visible and filterable in Django admin
- ✅ **Import compatibility**: Works with all import commands

---

## 🔍 **Verification Steps**

### **Check Database Schema:**
```bash
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"PRAGMA table_info(tracker_paper);\") # SQLite
# OR for PostgreSQL:
# cursor.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='tracker_paper';\")
rows = cursor.fetchall()
assessment_cols = [row for row in rows if 'assessment_tool' in str(row)]
print('Assessment tool column:', assessment_cols)
"
```

### **Test Import Command:**
```bash
# Try a small test first
python manage.py import_medical_papers_bulk your-file.csv --limit 100

# Should show:
# ✅ Papers imported successfully
# 📊 Assessment tool: rtransparent
```

### **Check Admin Interface:**
1. Visit: `http://your-domain.com/admin/tracker/paper/`
2. You should see "Assessment tool" column
3. Filter by "Assessment tool" should work

---

## 🎯 **Import Command Updates**

### **Now Supports:**
```python
# Filtering papers by assessment tool
Paper.objects.filter(assessment_tool='rtransparent')

# Creating papers with assessment tool tracking
Paper.objects.create(
    epmc_id='PMC123456',
    assessment_tool='rtransparent',
    # ... other fields
)

# Bulk operations with assessment tool
Paper.objects.bulk_create([
    Paper(epmc_id='PMC1', assessment_tool='rtransparent'),
    Paper(epmc_id='PMC2', assessment_tool='manual'),
])
```

### **Import Statistics:**
The import commands now track and report:
- **Total papers imported**
- **Papers by assessment tool**
- **Processing metadata**

---

## 💡 **Future Use Cases**

### **Assessment Tool Tracking:**
- `'rtransparent'` - Papers processed with R transparent package
- `'manual'` - Manually assessed papers
- `'odtap'` - Papers from ODTAP database
- `'mixed'` - Papers with multiple assessment sources

### **Filtering Examples:**
```bash
# Get all rtransparent papers
Paper.objects.filter(assessment_tool='rtransparent')

# Get papers from specific years with rtransparent
Paper.objects.filter(
    assessment_tool='rtransparent',
    pub_year__gte=2020
)

# Count papers by assessment tool
from django.db.models import Count
Paper.objects.values('assessment_tool').annotate(count=Count('id'))
```

---

## 🔧 **Troubleshooting**

### **If Migration Fails:**
```bash
# Check migration status
python manage.py showmigrations tracker

# If migration is stuck, reset and rerun
python manage.py migrate tracker 0003 --fake
python manage.py migrate tracker 0004
```

### **If Field Still Missing:**
```bash
# Reset migrations (careful - data loss risk)
python manage.py migrate tracker zero
python manage.py migrate tracker
```

### **Permission Issues:**
```bash
# Fix database permissions
sudo chown $USER:www-data ost_database.sqlite3  # SQLite
sudo chmod 664 ost_database.sqlite3

# For PostgreSQL
sudo -u postgres psql -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO ost_user;"
```

---

## ✅ **Success Indicators**

### **✅ Fixed When You See:**
```bash
# Import runs without field errors
✅ Processing medical papers: 2704359 rows...
✅ Papers imported successfully
📊 Total papers in database: 2,704,359
📊 Papers with rtransparent assessment: 2,704,359

# Admin interface shows assessment tool
✅ Assessment tool column visible
✅ Filter by assessment tool works

# API includes assessment tool
curl http://your-domain.com/api/papers/ | grep assessment_tool
```

---

## 🎊 **Ready to Import!**

Your medical papers import should now work flawlessly with proper assessment tool tracking!

**Command to run after applying this fix:**
```bash
cd /var/www/ost
source ost_env/bin/activate
python manage.py import_medical_papers_bulk rtransparent_csvs/medicaltransparency_opendata.csv
``` 