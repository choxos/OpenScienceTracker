#!/usr/bin/env python3
"""
Test script to validate the medical transparency data structure before full import.
This script will:
1. Check if the file exists and is readable
2. Display column structure and sample data
3. Test journal matching on a small sample
4. Estimate processing time and matches
"""

import os
import sys
import django
import pandas as pd

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal
from django.db.models import Q


def find_matching_journal(journal_title, journal_issn):
    """Find a matching journal in the database by ISSN or name"""
    journal = None
    
    # First try ISSN matching (most reliable)
    if journal_issn and pd.notna(journal_issn):
        issn_clean = str(journal_issn).strip()
        if issn_clean:
            journal = Journal.objects.filter(
                Q(issn_electronic=issn_clean) |
                Q(issn_print=issn_clean) |
                Q(issn_linking=issn_clean)
            ).first()
    
    # If no ISSN match, try journal name matching
    if not journal and journal_title and pd.notna(journal_title):
        title_clean = str(journal_title).strip()
        if title_clean:
            # Try exact matches first
            journal = Journal.objects.filter(
                Q(title_abbreviation__iexact=title_clean) |
                Q(title_full__iexact=title_clean)
            ).first()
            
            # If no exact match, try partial matches
            if not journal:
                journal = Journal.objects.filter(
                    Q(title_abbreviation__icontains=title_clean) |
                    Q(title_full__icontains=title_clean)
                ).first()
    
    return journal


def test_medical_data():
    """Test the medical transparency data structure"""
    file_path = 'papers/medicaltransparency_opendata.csv'
    
    print("🧪 Testing Medical Transparency Data")
    print("=" * 40)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        print("📝 Instructions:")
        print("   1. Place your medicaltransparency_opendata.csv file in the papers/ directory")
        print("   2. The file is already in .gitignore, so it won't be committed to Git")
        print("   3. Run this test script again to validate the data")
        return
    
    # Get file info
    file_size = os.path.getsize(file_path) / (1024 ** 3)  # GB
    print(f"✅ File found: {file_path}")
    print(f"📁 File size: {file_size:.2f} GB")
    
    try:
        # Read first few rows to check structure
        print("\n🔍 Reading sample data...")
        sample_df = pd.read_csv(file_path, nrows=100, encoding='latin-1')
        
        print(f"📊 Data structure:")
        print(f"   - Columns: {len(sample_df.columns)}")
        print(f"   - Sample rows: {len(sample_df)}")
        
        print(f"\n📋 Columns in medical data:")
        for i, col in enumerate(sample_df.columns, 1):
            print(f"   {i:2d}. {col}")
        
        # Check required columns
        required_cols = ['pmid', 'title', 'journalTitle', 'pubYear', 'authorString']
        optional_cols = ['pmcid', 'doi', 'journalIssn', 'issue', 'journalVolume', 'pageInfo', 
                        'pubType', 'isOpenAccess', 'inEPMC', 'inPMC', 'hasPDF', 'firstPublicationDate']
        transparency_cols = ['is_open_data', 'is_open_code', 'is_coi_pred', 'is_fund_pred', 'is_register_pred']
        
        print(f"\n✅ Required columns check:")
        for col in required_cols:
            status = "✅" if col in sample_df.columns else "❌"
            print(f"   {status} {col}")
        
        print(f"\n📦 Europe PMC columns check:")
        for col in optional_cols:
            status = "✅" if col in sample_df.columns else "⚠️ "
            print(f"   {status} {col}")
        
        print(f"\n🔍 Transparency indicator columns check:")
        for col in transparency_cols:
            status = "✅" if col in sample_df.columns else "⚠️ "
            print(f"   {status} {col}")
        
        # Sample data analysis
        print(f"\n📊 Sample data analysis:")
        print(f"   - Total journals in OST database: {Journal.objects.count():,}")
        print(f"   - Sample papers: {len(sample_df)}")
        
        # Test journal matching on sample
        print(f"\n🔗 Testing journal matching on sample...")
        matched_count = 0
        sample_matches = []
        
        for idx, row in sample_df.head(20).iterrows():
            journal_title = row.get('journalTitle')
            journal_issn = row.get('journalIssn')
            pmid = row.get('pmid')
            
            journal = find_matching_journal(journal_title, journal_issn)
            if journal:
                matched_count += 1
                sample_matches.append({
                    'pmid': pmid,
                    'journal_title': journal_title,
                    'journal_issn': journal_issn,
                    'matched_journal': journal.title_abbreviation,
                    'subject_category': journal.broad_subject_terms.split(';')[0] if journal.broad_subject_terms else 'Unknown'
                })
        
        print(f"   - Sample matches: {matched_count}/20 ({(matched_count/20)*100:.1f}%)")
        
        if sample_matches:
            print(f"\n🎯 Sample successful matches:")
            for match in sample_matches[:5]:
                print(f"   - PMID {match['pmid']}: {match['journal_title']} -> {match['matched_journal']} ({match['subject_category']})")
        
        # Check for existing papers (duplicates)
        existing_count = 0
        sample_pmids = sample_df['pmid'].dropna().head(100).tolist()
        for pmid in sample_pmids:
            if Paper.objects.filter(pmid=str(pmid)).exists():
                existing_count += 1
        
        print(f"\n🔄 Duplicate check (first 100 PMIDs):")
        print(f"   - Already in database: {existing_count}/100")
        print(f"   - New papers: {100-existing_count}/100")
        
        # Estimate total processing
        try:
            total_rows = len(pd.read_csv(file_path, usecols=[0], encoding='latin-1'))
            estimated_matches = int((matched_count / 20) * total_rows)
            print(f"\n📈 Processing estimates:")
            print(f"   - Total rows in file: {total_rows:,}")
            print(f"   - Estimated journal matches: {estimated_matches:,}")
            print(f"   - Estimated processing time: {(total_rows / 10000) * 2:.0f}-{(total_rows / 10000) * 5:.0f} minutes")
        except:
            print(f"\n📈 Unable to estimate total rows (file too large for quick count)")
        
        print(f"\n✅ Data validation completed!")
        print(f"🚀 Ready to run: python import_medical_transparency_data.py")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        print("💡 Try checking the file encoding or format")


if __name__ == "__main__":
    test_medical_data() 