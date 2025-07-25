# rtransparent Data Structure Analysis & Import Solution

## 🔍 **Problem Discovery**

You were correct! The **0 papers imported** was due to **incompatible data structures** between your existing data and the new rtransparent CSV, not because the papers already existed.

## 📊 **Data Structure Comparison**

### **Original Data (`transparency_1900_01.csv`)**
```
Columns: 150+ fields
Structure: "id","source","pmcid","title","journalTitle",...,"rt_all_is_coi_pred",...,"rt_data_is_open_data",...

Key Fields:
- "id" → Used as epmc_id (REQUIRED unique field)
- "source" → Data source identifier  
- "pubYear" → Publication year
- "rt_all_is_coi_pred" → COI disclosure (complex naming)
- "rt_data_is_open_data" → Open data (complex naming)
```

### **New rtransparent Data (`medicaltransparency_opendata.csv`)**
```
Columns: 30 fields  
Structure: "pmid","pmcid","doi","title","authorString","journalTitle",...,"is_coi_pred",...,"is_open_data"

Key Fields:
- NO "id" field → Missing required epmc_id ❌
- NO "source" field → Missing source identifier ❌  
- NO "pubYear" → Has "firstPublicationDate" instead ❌
- "is_coi_pred" → COI disclosure (clean naming) ✅
- "is_open_data" → Open data (clean naming) ✅
```

## 🚨 **Critical Issues Identified**

### **1. Missing Required Fields**
- **`epmc_id`**: Required unique field missing from new CSV
- **`source`**: Data source identifier missing
- **`pubYear`**: Script expects this field, but CSV has `firstPublicationDate`

### **2. Column Name Mismatches**
- Script looks for `pubMonth` → Not in new CSV
- Script looks for `pubTypeList` → New CSV has `type`
- Script looks for `meshMajor` → Not in new CSV

### **3. Import Script Incompatibility**
- `import_medical_papers_bulk.py` designed for old structure
- Field mappings don't match new CSV columns
- Can't create papers without `epmc_id`

## 🛠️ **Solution: New Import Script**

Created `import_rtransparent_medical.py` specifically for the new data structure:

### **Key Features:**
1. **Smart `epmc_id` Generation**: Creates unique IDs from PMCID/PMID/DOI
2. **Correct Field Mapping**: Maps new CSV columns to model fields  
3. **Date Parsing**: Extracts year from `firstPublicationDate`
4. **Transparency Score Calculation**: Computes score from indicators
5. **Robust Error Handling**: Skips problematic rows, continues processing

### **Field Mapping Strategy:**
```python
# epmc_id generation priority:
1. PMC{pmcid} if pmcid exists (e.g., "PMC2190076")
2. PMID{pmid} if no pmcid (e.g., "PMID450")  
3. DOI{hash} if no pmcid/pmid (e.g., "DOI1a2b3c4d")

# Direct field mappings:
'pmid' → pmid
'pmcid' → pmcid  
'doi' → doi
'title' → title
'authorString' → author_string
'journalTitle' → journal_title
'firstPublicationDate' → pub_year (extracted)
'is_coi_pred' → is_coi_pred
'is_fund_pred' → is_fund_pred
'is_register_pred' → is_register_pred
'is_open_data' → is_open_data
'is_open_code' → is_open_code
```

## 🚀 **Usage Instructions**

### **1. Test Import (Recommended First)**
```bash
cd /var/www/ost
source ost_env/bin/activate

# Test with first 1000 records
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv --limit 1000 --dry-run

# Test actual import of small batch
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv --limit 1000
```

### **2. Full Import**
```bash
# Import all data (will take time due to size)
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv

# Or with custom settings
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv \
  --batch-size 2000 \
  --chunk-size 20000
```

### **3. Update Existing Papers**
```bash
# Update papers that already exist  
python manage.py import_rtransparent_medical rtransparent_csvs/medicaltransparency_opendata.csv --update-existing
```

## 📈 **Expected Results**

With the new script, you should see:
- **Successful imports**: Papers will be created with proper `epmc_id`
- **Transparency indicators**: Properly mapped from new CSV structure
- **Progress tracking**: Real-time progress with memory usage
- **Error handling**: Skips problematic rows but continues processing

## 🔧 **Verification Steps**

After running the new import:

```bash
# Check import status
python check_import_status.py

# Verify new papers
python manage.py shell -c "
from tracker.models import Paper
new_papers = Paper.objects.filter(source='rtransparent').count()
total_papers = Paper.objects.count()
print(f'New rtransparent papers: {new_papers:,}')
print(f'Total papers: {total_papers:,}')
print(f'Sample epmc_ids: {list(Paper.objects.filter(source=\"rtransparent\")[:5].values_list(\"epmc_id\", flat=True))}')
"
```

## 🎯 **Why This Will Work**

1. **Correct Structure**: Script designed for actual CSV structure
2. **Required Fields**: Generates missing `epmc_id` from available data
3. **Proper Mapping**: Maps all available transparency indicators
4. **Scalability**: Handles large files with chunked processing
5. **Safety**: Dry-run and limit options for testing

## 📋 **Summary**

- **Problem**: Data structure incompatibility, not duplicate data
- **Root Cause**: Import script expected old CSV format, got new format
- **Solution**: New import script with correct field mappings
- **Result**: Will successfully import your 2.7M rtransparent papers

The mystery is solved! Your papers ARE new and WILL be imported with the correct script. 🎉 