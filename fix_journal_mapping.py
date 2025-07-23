#!/usr/bin/env python3
"""
Script to fix journal mapping and re-import medical data properly.
This addresses the issue where all papers are incorrectly assigned to one journal.
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.production_settings')
django.setup()

from tracker.models import Paper, Journal
from django.db import transaction, connection
from django.db.models import Count

def check_current_state():
    """Check current database state"""
    print("🔍 CHECKING CURRENT DATABASE STATE...")
    
    total_papers = Paper.objects.count()
    total_journals = Journal.objects.count()
    
    print(f"📊 Total papers: {total_papers:,}")
    print(f"📚 Total journals: {total_journals:,}")
    
    # Check journal distribution
    journal_paper_counts = Paper.objects.values('journal__title_abbreviation').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    print("\n📈 Top 10 journals by paper count:")
    for item in journal_paper_counts:
        journal_name = item['journal__title_abbreviation'] or 'Unknown'
        count = item['count']
        print(f"  {journal_name}: {count:,} papers")
    
    # Check if we have the problematic mapping
    problem_journal = Paper.objects.filter(journal__title_abbreviation='20 Century Br Hist').count()
    if problem_journal > 100000:
        print(f"\n❌ PROBLEM DETECTED: {problem_journal:,} papers assigned to '20 Century Br Hist'")
        return True
    else:
        print("\n✅ Journal distribution looks healthy")
        return False

def build_comprehensive_journal_mapping():
    """Build a comprehensive journal mapping dictionary"""
    print("\n📚 Building comprehensive journal mapping...")
    
    journal_map = {}
    journals = Journal.objects.all()
    
    for journal in journals:
        j_id = journal.id
        
        # Map by exact title abbreviation
        if journal.title_abbreviation:
            key = f"title_abbrev:{journal.title_abbreviation.strip().lower()}"
            journal_map[key] = j_id
        
        # Map by exact title full
        if journal.title_full:
            key = f"title_full:{journal.title_full.strip().lower()}"
            journal_map[key] = j_id
        
        # Map by NLM ID if available
        if journal.nlm_id:
            key = f"nlm:{journal.nlm_id.strip()}"
            journal_map[key] = j_id
        
        # Map by ISSNs
        if journal.issn_print:
            key = f"issn:{journal.issn_print.strip()}"
            journal_map[key] = j_id
        if journal.issn_electronic:
            key = f"issn:{journal.issn_electronic.strip()}"
            journal_map[key] = j_id
    
    print(f"📋 Created {len(journal_map)} journal mapping entries")
    return journal_map

def find_correct_journal_id(row, journal_map, unmapped_journals):
    """Find the correct journal ID for a paper with improved logic"""
    
    # Method 1: Try exact journal title match
    journal_title = str(row.get('journalTitle', '')).strip()
    if journal_title and journal_title != 'nan':
        # Try title abbreviation match
        key = f"title_abbrev:{journal_title.lower()}"
        if key in journal_map:
            return journal_map[key]
        
        # Try full title match
        key = f"title_full:{journal_title.lower()}"
        if key in journal_map:
            return journal_map[key]
        
        # Try partial matches for common abbreviations
        for map_key, j_id in journal_map.items():
            if map_key.startswith('title_') and journal_title.lower() in map_key:
                return j_id
    
    # Method 2: Try ISSN match
    journal_issn = str(row.get('journalIssn', '')).strip()
    if journal_issn and journal_issn != 'nan':
        # Handle multiple ISSNs
        issns = [issn.strip() for issn in journal_issn.split(';') if issn.strip()]
        for issn in issns:
            key = f"issn:{issn}"
            if key in journal_map:
                return journal_map[key]
    
    # Method 3: Log unmapped journal for analysis
    if journal_title and journal_title != 'nan':
        unmapped_journals[journal_title] += 1
    
    # Method 4: Return None instead of fallback (we'll handle this specially)
    return None

def create_unknown_journals(unmapped_journals):
    """Create journal entries for unmapped journals"""
    print(f"\n🆕 Creating journals for {len(unmapped_journals)} unmapped journal names...")
    
    created_journals = {}
    
    for journal_name, count in unmapped_journals.most_common():
        if count < 5:  # Skip journals with very few papers
            continue
            
        # Create a new journal entry
        journal, created = Journal.objects.get_or_create(
            title_abbreviation=journal_name[:200],  # Truncate to fit field
            defaults={
                'title_full': journal_name,
                'broad_subject_terms': 'Medicine',
                'subject_term_count': 1,
                'country': 'Unknown',
                'language': 'Unknown',
            }
        )
        
        if created:
            created_journals[journal_name] = journal.id
            print(f"  ✅ Created journal: {journal_name} (ID: {journal.id})")
    
    return created_journals

def clear_medical_papers():
    """Clear papers that are incorrectly mapped to preserve dental data"""
    print("\n🗑️ Clearing incorrectly mapped medical papers...")
    
    # Identify papers that are likely medical imports (not dental)
    # We'll clear papers from journals that have unusually high paper counts
    problematic_journals = Paper.objects.values('journal').annotate(
        count=Count('id')
    ).filter(count__gt=50000)  # Journals with >50k papers are likely incorrectly mapped
    
    problematic_journal_ids = [item['journal'] for item in problematic_journals]
    
    if problematic_journal_ids:
        papers_to_delete = Paper.objects.filter(journal_id__in=problematic_journal_ids)
        count_to_delete = papers_to_delete.count()
        
        print(f"📊 Found {count_to_delete:,} papers in {len(problematic_journal_ids)} problematic journals")
        
        # Delete in batches to avoid memory issues
        batch_size = 10000
        deleted_total = 0
        
        while papers_to_delete.exists():
            batch = list(papers_to_delete.values_list('id', flat=True)[:batch_size])
            Paper.objects.filter(id__in=batch).delete()
            deleted_total += len(batch)
            print(f"  🗑️ Deleted {deleted_total:,} / {count_to_delete:,} papers...")
        
        print(f"✅ Deleted {deleted_total:,} incorrectly mapped papers")
    else:
        print("✅ No problematic journal mappings found")

def reimport_medical_data():
    """Re-import medical data with proper journal mapping"""
    print("\n📥 Re-importing medical data with correct journal mapping...")
    
    # Look for the medical data file
    csv_files = [
        'rtransparent_csvs/medicaltransparency_opendata.csv',
        'medicaltransparency_opendata.csv',
        'medical_transparency_data.csv'
    ]
    
    csv_file = None
    for file_path in csv_files:
        if os.path.exists(file_path):
            csv_file = file_path
            break
    
    if not csv_file:
        print("❌ Medical transparency CSV file not found")
        return False
    
    print(f"📄 Using file: {csv_file}")
    
    # Build journal mapping
    journal_map = build_comprehensive_journal_mapping()
    unmapped_journals = defaultdict(int)
    
    # Read CSV in chunks for memory efficiency
    chunk_size = 10000
    total_imported = 0
    total_processed = 0
    
    print(f"📊 Processing CSV in chunks of {chunk_size}...")
    
    for chunk_num, chunk_df in enumerate(pd.read_csv(csv_file, chunksize=chunk_size, low_memory=False), 1):
        chunk_df = chunk_df.fillna('')
        
        papers = []
        skipped_no_journal = 0
        
        for idx, row in chunk_df.iterrows():
            # Find correct journal ID
            journal_id = find_correct_journal_id(row, journal_map, unmapped_journals)
            
            if journal_id is None:
                skipped_no_journal += 1
                continue  # Skip papers we can't map to journals
            
            # Create Paper instance with proper journal mapping
            paper = Paper(
                pmid=str(row.get('pmid', ''))[:20] or f"MISSING_{idx}",
                pmcid=str(row.get('pmcid', ''))[:20] or None,
                doi=str(row.get('doi', '')) or None,
                title=str(row.get('title', '')) or 'Unknown Title',
                author_string=str(row.get('authorString', '')) or '',
                journal_title=str(row.get('journalTitle', '')) or 'Unknown Journal',
                journal_issn=str(row.get('journalIssn', ''))[:9] or None,
                pub_year=int(float(row.get('pubYear', 2020))) if str(row.get('pubYear', '')).replace('.','').isdigit() else 2020,
                
                # Transparency indicators
                is_coi_pred=str(row.get('is_coi_pred', '')).upper() in ['TRUE', '1', 'YES', 'T', 'Y'],
                is_fund_pred=str(row.get('is_fund_pred', '')).upper() in ['TRUE', '1', 'YES', 'T', 'Y'],
                is_register_pred=str(row.get('is_register_pred', '')).upper() in ['TRUE', '1', 'YES', 'T', 'Y'],
                is_open_data=str(row.get('is_open_data', '')).upper() in ['TRUE', '1', 'YES', 'T', 'Y'],
                is_open_code=str(row.get('is_open_code', '')).upper() in ['TRUE', '1', 'YES', 'T', 'Y'],
                
                transparency_score=int(float(row.get('transparency_score', 0))) if str(row.get('transparency_score', '')).replace('.','').isdigit() else 0,
                transparency_score_pct=float(row.get('transparency_score_pct', 0)) if str(row.get('transparency_score_pct', '')).replace('.','').isdigit() else 0.0,
                
                # Assessment metadata
                assessment_tool='rtransparent',
                ost_version='1.0',
                
                # Subject classification
                broad_subject_category=str(row.get('meshMajor', '')) or None,
                
                # Proper journal reference
                journal_id=journal_id,
            )
            papers.append(paper)
        
        # Bulk insert the batch
        if papers:
            with transaction.atomic():
                Paper.objects.bulk_create(papers, ignore_conflicts=True)
            total_imported += len(papers)
        
        total_processed += len(chunk_df)
        
        print(f"  📦 Chunk {chunk_num}: Imported {len(papers)}, Skipped {skipped_no_journal}, Total: {total_imported:,}")
        
        # Limit for testing (remove this line for full import)
        if total_processed >= 50000:  # Process only first 50k rows for testing
            print(f"⚠️ Stopping at {total_processed:,} rows for testing")
            break
    
    # Create journals for unmapped ones if significant
    if unmapped_journals:
        print(f"\n📊 Top 10 unmapped journals:")
        for journal_name, count in unmapped_journals.most_common(10):
            print(f"  {journal_name}: {count} papers")
        
        # Optionally create journals for frequently unmapped ones
        created_journals = create_unknown_journals(unmapped_journals)
        
        # Could re-process unmapped papers here if needed
    
    print(f"\n✅ Import completed: {total_imported:,} papers imported")
    return True

def validate_results():
    """Validate the import results"""
    print("\n✅ VALIDATING IMPORT RESULTS...")
    
    total_papers = Paper.objects.count()
    total_journals = Journal.objects.count()
    
    print(f"📊 Total papers: {total_papers:,}")
    print(f"📚 Total journals: {total_journals:,}")
    
    # Check journal distribution
    journal_distribution = Paper.objects.values('journal__title_abbreviation').annotate(
        count=Count('id')
    ).order_by('-count')[:15]
    
    print("\n📈 Top 15 journals by paper count:")
    for item in journal_distribution:
        journal_name = item['journal__title_abbreviation'] or 'Unknown'
        count = item['count']
        print(f"  {journal_name}: {count:,} papers")
    
    # Check for the problematic mapping
    problem_journal = Paper.objects.filter(journal__title_abbreviation='20 Century Br Hist').count()
    if problem_journal > 1000:
        print(f"\n⚠️ WARNING: Still {problem_journal:,} papers assigned to '20 Century Br Hist'")
        return False
    else:
        print(f"\n✅ SUCCESS: Only {problem_journal} papers assigned to '20 Century Br Hist'")
        return True

def main():
    """Main execution function"""
    print("🔧 FIXING JOURNAL MAPPING AND RE-IMPORTING MEDICAL DATA")
    print("=" * 60)
    
    # Step 1: Check current state
    has_problem = check_current_state()
    
    if not has_problem:
        print("\n✅ No journal mapping problems detected. Exiting.")
        return
    
    # Step 2: Clear incorrectly mapped papers
    clear_medical_papers()
    
    # Step 3: Re-import with proper mapping
    success = reimport_medical_data()
    
    if not success:
        print("\n❌ Import failed. Check error messages above.")
        return
    
    # Step 4: Validate results
    validation_success = validate_results()
    
    if validation_success:
        print("\n🎉 SUCCESS! Journal mapping has been fixed.")
        print("📊 Run this to see final statistics:")
        print("python manage.py shell -c \"from tracker.models import Paper, Journal; print(f'Papers: {Paper.objects.count():,}, Journals: {Journal.objects.count():,}')\"")
    else:
        print("\n⚠️ Validation failed. Manual review may be needed.")

if __name__ == "__main__":
    main() 