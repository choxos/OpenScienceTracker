# 🗃️ **Database Migration Guide**

This guide helps you apply database migrations, especially for the new transparency averages features in ResearchField.

## 🚨 **Current Issue Fix**

If you see this error:
```
OperationalError: no such column: tracker_researchfield.avg_data_sharing
```

**You need to apply the database migration!**

## 🔧 **Local Development Fix**

### **Step 1: Apply Migration**
```bash
# Navigate to project directory
cd /path/to/OpenScienceTracker

# Activate virtual environment (if using one)
source ost_env/bin/activate  # Linux/Mac
# OR
ost_env\Scripts\activate     # Windows

# Apply the migration
python manage.py migrate
```

### **Step 2: Populate Fields**
```bash
# Update research fields with transparency averages
python manage.py populate_research_fields_from_nlm --update-existing
```

### **Step 3: Test**
```bash
# Start development server
python manage.py runserver

# Visit http://localhost:8000/fields/
# Should now work without errors!
```

## 🚀 **Production VPS Fix**

### **Method 1: Using Deploy Script**
```bash
# SSH to your VPS
ssh user@your-vps-ip

# Navigate to project
cd /var/www/opensciencetracker

# Run deployment script (includes migrations)
./deploy.sh
```

### **Method 2: Manual Migration**
```bash
# SSH to your VPS
ssh user@your-vps-ip

# Navigate to project
cd /var/www/opensciencetracker

# Activate virtual environment
source ost_env/bin/activate

# Apply migration
python manage.py migrate

# Update research fields
python manage.py populate_research_fields_from_nlm --update-existing

# Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## 📊 **What the Migration Does**

### **Adds 6 New Columns to ResearchField:**
- `avg_data_sharing` - % of papers with open data
- `avg_code_sharing` - % of papers with open code  
- `avg_coi_disclosure` - % of papers with COI disclosure
- `avg_funding_disclosure` - % of papers with funding info
- `avg_protocol_registration` - % of papers with registration
- `avg_open_access` - % of papers with open access

### **Before Migration:**
```sql
-- ResearchField table
id | name | total_papers | avg_transparency_score
1  | Medicine | 176 | 2.5
```

### **After Migration:**
```sql
-- ResearchField table (with new columns)
id | name | total_papers | avg_transparency_score | avg_data_sharing | avg_code_sharing | avg_coi_disclosure
1  | Medicine | 176 | 2.5 | 15.2 | 8.7 | 45.3
```

## 🔍 **Verify Migration Success**

### **Check Database Schema:**
```bash
# Connect to database
python manage.py dbshell

# Check if columns exist (SQLite)
.schema tracker_researchfield

# OR (PostgreSQL)
\d tracker_researchfield
```

### **Check in Django Shell:**
```bash
python manage.py shell

# Test field access
>>> from tracker.models import ResearchField
>>> field = ResearchField.objects.first()
>>> print(field.avg_data_sharing)  # Should not error
>>> print(field.avg_code_sharing)  # Should show percentage
```

### **Check Web Interface:**
```bash
# Visit these URLs - should work without errors:
http://localhost:8000/fields/           # Local
https://your-domain.com/fields/         # Production
```

## 🚨 **Troubleshooting**

### **Migration Doesn't Apply:**
```bash
# Check migration status
python manage.py showmigrations tracker

# If migration is listed but not applied:
python manage.py migrate tracker 0003

# If migration file is missing:
python manage.py makemigrations tracker
python manage.py migrate
```

### **Fields Show Zero Values:**
```bash
# Recalculate transparency averages
python manage.py populate_research_fields_from_nlm --update-existing

# Check specific field
python manage.py shell
>>> from tracker.models import ResearchField
>>> field = ResearchField.objects.get(name='Medicine')
>>> print(f"Papers: {field.total_papers}")
>>> print(f"Data sharing: {field.avg_data_sharing}%")
```

### **Permission Errors (VPS):**
```bash
# Fix file permissions
sudo chown -R www-data:www-data /var/www/opensciencetracker/
sudo chmod -R 755 /var/www/opensciencetracker/

# Fix database permissions
sudo chown www-data:www-data /var/www/opensciencetracker/ost_database.sqlite3
```

## 📈 **Expected Results**

### **Field List Page:**
- ✅ Shows individual transparency percentages for each field
- ✅ Displays "Papers: X, Journals: Y, Transparency Score: Z/6"
- ✅ Shows: Open Data %, Open Code %, COI Disclosure %, etc.

### **Database Content:**
- ✅ Medicine field: ~176 papers with calculated averages
- ✅ Public Health field: ~4 papers with calculated averages
- ✅ 125+ research fields with transparency statistics

## 🎯 **Migration Complete Checklist**

- [ ] Migration applied without errors
- [ ] Field list page loads (`/fields/`)
- [ ] Individual transparency percentages display
- [ ] No "column does not exist" errors
- [ ] Research fields show calculated averages
- [ ] Web interface displays colorful transparency indicators

## 📞 **Support**

If you encounter issues:
1. **Check migration status**: `python manage.py showmigrations`
2. **Review error logs**: `tail -f /var/log/gunicorn.log`
3. **Test in Django shell**: Verify field access works
4. **Restart services**: Ensure web server picks up changes

**Migration successfully transforms your fields page from basic counts to comprehensive transparency analytics! 📊✨** 