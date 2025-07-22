#!/usr/bin/env python3
import os
import sys
import django

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal
from django.db.models import Q
import pandas as pd

def test_journal_matching():
    """Test journal matching with medical data sample"""
    print("🔍 Testing Journal Matching with Medical Data")
    print("=" * 50)
    
    # Read sample data
    df = pd.read_csv('papers/medicaltransparency_opendata.csv', nrows=10, encoding='latin-1')
    
    print(f"📊 Testing {len(df)} sample papers...")
    print(f"🏥 Total journals in OST database: {Journal.objects.count():,}")
    
    matches_found = 0
    
    for idx, row in df.iterrows():
        journal_title = row.get('journalTitle', '')
        journal_issn = row.get('journalIssn', '')
        
        print(f"\n📋 Paper {idx+1}:")
        print(f"   Title: {journal_title}")
        print(f"   ISSN: {journal_issn}")
        
        # Parse multiple ISSNs (separated by semicolons)
        issn_list = []
        if pd.notna(journal_issn) and journal_issn:
            issn_list = [issn.strip() for issn in str(journal_issn).split(';') if issn.strip()]
        
        # Try ISSN matching
        journal = None
        for issn in issn_list:
            if issn:
                journal = Journal.objects.filter(
                    Q(issn_electronic=issn) |
                    Q(issn_print=issn) |
                    Q(issn_linking=issn)
                ).first()
                if journal:
                    print(f"   ✅ ISSN Match ({issn}): {journal.title_abbreviation}")
                    print(f"      Category: {journal.broad_subject_terms}")
                    matches_found += 1
                    break
                else:
                    print(f"   ❌ ISSN {issn}: No match")
        
        # If no ISSN match, try name matching
        if not journal and pd.notna(journal_title) and journal_title:
            # Try exact matches
            journal = Journal.objects.filter(
                Q(title_abbreviation__iexact=journal_title) |
                Q(title_full__iexact=journal_title)
            ).first()
            
            if journal:
                print(f"   ✅ Name Match (exact): {journal.title_abbreviation}")
                print(f"      Category: {journal.broad_subject_terms}")
                matches_found += 1
            else:
                # Try partial matches
                journal = Journal.objects.filter(
                    Q(title_abbreviation__icontains=journal_title) |
                    Q(title_full__icontains=journal_title)
                ).first()
                
                if journal:
                    print(f"   ✅ Name Match (partial): {journal.title_abbreviation}")
                    print(f"      Category: {journal.broad_subject_terms}")
                    matches_found += 1
                else:
                    print(f"   ❌ No name match for: {journal_title}")
        
        if not journal:
            print(f"   ⚠️  NO MATCH FOUND")
    
    print(f"\n📊 Results:")
    print(f"   - Total tested: {len(df)}")
    print(f"   - Matches found: {matches_found}")
    print(f"   - Match rate: {(matches_found/len(df))*100:.1f}%")
    
    # Show some sample journals from our database
    print(f"\n📋 Sample journals in OST database:")
    sample_journals = Journal.objects.all()[:10]
    for journal in sample_journals:
        print(f"   - {journal.title_abbreviation} ({journal.issn_print or journal.issn_electronic or 'No ISSN'})")
        print(f"     Full: {journal.title_full}")
        print(f"     Category: {journal.broad_subject_terms}")

if __name__ == "__main__":
    test_journal_matching() 