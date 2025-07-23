#!/usr/bin/env python3
"""
Test dental journals import locally before deploying to Railway
This script tests the import process on your local SQLite database
"""

import os
import sys
import django
import pandas as pd

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal, ResearchField

def test_dental_import():
    """Test the dental journals import locally"""
    print("🦷 Testing Dental Journals Import (Local)")
    print("=" * 50)
    
    # Check if CSV file exists
    csv_file = 'dental_journals_ost.csv'
    if not os.path.exists(csv_file):
        print(f"❌ Error: {csv_file} not found")
        return False
    
    # Load and analyze the CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"📄 Loaded {len(df):,} dental journal records")
        
        # Show sample data
        print(f"\n📊 Sample dental journals:")
        sample_data = df[['title_abbreviation', 'title_full', 'country', 'broad_subject_terms']].head(3)
        print(sample_data.to_string(index=False))
        
        # Analyze the data
        print(f"\n📈 Data Analysis:")
        print(f"   - Total records: {len(df):,}")
        print(f"   - Unique countries: {df['country'].nunique()}")
        print(f"   - Records with 'Dentistry' term: {df['broad_subject_terms'].str.contains('Dentistry', na=False).sum():,}")
        print(f"   - Records with titles: {df['title_full'].notna().sum():,}")
        
        # Check current database
        current_journals = Journal.objects.count()
        dental_journals = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
        
        print(f"\n🗄️  Current Database:")
        print(f"   - Total journals: {current_journals:,}")
        print(f"   - Dental journals: {dental_journals:,}")
        
        # Estimate what would be imported
        existing_nlm_ids = set(Journal.objects.values_list('nlm_id', flat=True))
        new_journals = []
        
        for _, row in df.iterrows():
            nlm_id = str(row.get('nlm_id', '')).strip()
            if nlm_id and nlm_id != 'nan' and nlm_id not in existing_nlm_ids:
                new_journals.append(nlm_id)
        
        print(f"\n🔮 Import Estimation:")
        print(f"   - New journals to be added: {len(new_journals):,}")
        print(f"   - Existing journals that would be updated: {len(df) - len(new_journals):,}")
        
        if len(new_journals) > 0:
            print(f"   - Sample new journal NLM IDs: {new_journals[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        return False

def test_import_single_record():
    """Test importing a single dental journal record"""
    print(f"\n🧪 Testing Single Record Import...")
    
    try:
        df = pd.read_csv('dental_journals_ost.csv')
        test_record = df.iloc[0]  # First record
        
        print(f"📝 Test record:")
        print(f"   - NLM ID: {test_record.get('nlm_id')}")
        print(f"   - Title: {test_record.get('title_abbreviation')}")
        print(f"   - Country: {test_record.get('country')}")
        print(f"   - Subject: {test_record.get('broad_subject_terms')}")
        
        # Try to create/get this journal
        nlm_id = str(test_record.get('nlm_id', '')).strip()
        if nlm_id and nlm_id != 'nan':
            journal, created = Journal.objects.get_or_create(
                nlm_id=nlm_id,
                defaults={
                    'title_abbreviation': str(test_record.get('title_abbreviation', 'Test')).strip(),
                    'title_full': str(test_record.get('title_full', '')).strip(),
                    'country': str(test_record.get('country', '')).strip(),
                    'broad_subject_terms': str(test_record.get('broad_subject_terms', '')).strip(),
                }
            )
            
            if created:
                print(f"✅ Successfully created test journal: {journal.title_abbreviation}")
                # Clean up - delete the test record
                journal.delete()
                print(f"🧹 Cleaned up test record")
            else:
                print(f"✅ Test journal already exists: {journal.title_abbreviation}")
            
            return True
        else:
            print(f"❌ Invalid NLM ID in test record")
            return False
            
    except Exception as e:
        print(f"❌ Error in single record test: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Dental Journals Import - Local Testing")
    print("This will test the import process without affecting your Railway database")
    print("=" * 70)
    
    # Test the data analysis
    if not test_dental_import():
        print("\n❌ Data analysis failed")
        return
    
    # Test single record import
    if not test_import_single_record():
        print("\n❌ Single record test failed")
        return
    
    print(f"\n✅ All tests passed!")
    print(f"\n📋 Next Steps:")
    print(f"   1. If everything looks good, deploy to Railway:")
    print(f"      python deploy_dental_journals_railway.py")
    print(f"   2. Or run the import directly on Railway:")
    print(f"      railway run python import_dental_journals_to_railway.py")
    print(f"   3. Check results at: https://ost.xeradb.com/journals/")

if __name__ == "__main__":
    main() 