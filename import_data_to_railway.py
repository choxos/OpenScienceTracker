#!/usr/bin/env python3
"""
Import OST data from JSON files into Railway PostgreSQL database
Run this script on Railway after deployment to populate the database
"""

import os
import sys
import django
import json
from datetime import datetime
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal

def import_data():
    """Import all data from JSON files"""
    print("📥 Importing OST Data to Railway PostgreSQL")
    print("=" * 50)
    
    data_dir = 'railway_data'
    if not os.path.exists(data_dir):
        print(f"❌ Error: {data_dir} directory not found")
        print("Please ensure the data export files are available")
        return
    
    # Load manifest
    manifest_file = os.path.join(data_dir, 'manifest.json')
    if not os.path.exists(manifest_file):
        print(f"❌ Error: manifest.json not found")
        return
    
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    print(f"📋 Data manifest loaded:")
    print(f"   - Export date: {manifest['export_date']}")
    print(f"   - Total journals: {manifest['total_journals']:,}")
    print(f"   - Total papers: {manifest['total_papers']:,}")
    print(f"   - Paper chunks: {manifest['paper_chunks']}")
    
    # Import journals first
    print(f"\n📚 Importing journals...")
    journals_file = os.path.join(data_dir, 'journals.json')
    
    with open(journals_file, 'r', encoding='utf-8') as f:
        journals_data = json.load(f)
    
    journal_map = {}  # nlm_id -> Journal object
    
    with transaction.atomic():
        for journal_data in journals_data:
            journal, created = Journal.objects.get_or_create(
                nlm_id=journal_data['nlm_id'],
                defaults={
                    'title_abbreviation': journal_data['title_abbreviation'],
                    'title_full': journal_data['title_full'] or '',
                    'authors': journal_data['authors'] or '',
                    'publication_start_year': journal_data['publication_start_year'],
                    'publication_end_year': journal_data['publication_end_year'],
                    'frequency': journal_data['frequency'] or '',
                    'country': journal_data['country'] or '',
                    'publisher': journal_data['publisher'] or '',
                    'language': journal_data['language'] or '',
                    'issn_electronic': journal_data['issn_electronic'] or '',
                    'issn_print': journal_data['issn_print'] or '',
                    'issn_linking': journal_data['issn_linking'] or '',
                    'indexing_status': journal_data['indexing_status'] or '',
                    'broad_subject_terms': journal_data['broad_subject_terms'] or '',
                    'subject_term_count': journal_data['subject_term_count'] or 0,
                    'mesh_terms': journal_data['mesh_terms'] or '',
                    'lccn': journal_data['lccn'] or '',
                    'electronic_links': journal_data['electronic_links'] or '',
                    'publication_types': journal_data['publication_types'] or '',
                    'notes': journal_data['notes'] or '',
                }
            )
            journal_map[journal_data['nlm_id']] = journal
    
    print(f"   ✅ Imported {len(journals_data):,} journals")
    
    # Import papers in chunks
    print(f"\n📄 Importing papers...")
    total_papers_imported = 0
    
    for chunk_num in range(manifest['paper_chunks']):
        chunk_file = os.path.join(data_dir, f"papers_chunk_{chunk_num + 1:03d}.json")
        
        if not os.path.exists(chunk_file):
            print(f"   ⚠️  Warning: {chunk_file} not found, skipping...")
            continue
        
        with open(chunk_file, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
        
        papers_created = 0
        papers_skipped = 0
        
        with transaction.atomic():
            for paper_data in papers_data:
                # Skip if paper already exists
                if Paper.objects.filter(pmid=paper_data['pmid']).exists():
                    papers_skipped += 1
                    continue
                
                # Find journal
                journal = None
                if paper_data['journal_nlm_id']:
                    journal = journal_map.get(paper_data['journal_nlm_id'])
                
                # Parse dates
                first_pub_date = None
                if paper_data['first_publication_date']:
                    try:
                        first_pub_date = datetime.fromisoformat(paper_data['first_publication_date']).date()
                    except:
                        pass
                
                assessment_date = None
                if paper_data['assessment_date']:
                    try:
                        assessment_date = datetime.fromisoformat(paper_data['assessment_date']).date()
                    except:
                        pass
                
                # Create paper
                paper = Paper(
                    pmid=paper_data['pmid'],
                    pmcid=paper_data['pmcid'] or '',
                    doi=paper_data['doi'] or '',
                    title=paper_data['title'],
                    author_string=paper_data['author_string'],
                    journal=journal,
                    journal_title=paper_data['journal_title'],
                    pub_year=paper_data['pub_year'],
                    issue=paper_data['issue'] or '',
                    page_info=paper_data['page_info'] or '',
                    journal_volume=paper_data['journal_volume'] or '',
                    pub_type=paper_data['pub_type'] or '',
                    is_open_access=paper_data['is_open_access'] or False,
                    in_epmc=paper_data['in_epmc'] or False,
                    in_pmc=paper_data['in_pmc'] or False,
                    has_pdf=paper_data['has_pdf'] or False,
                    first_publication_date=first_pub_date,
                    journal_issn=paper_data['journal_issn'] or '',
                    broad_subject_category=paper_data['broad_subject_category'],
                    is_open_data=paper_data['is_open_data'] or False,
                    is_open_code=paper_data['is_open_code'] or False,
                    is_coi_pred=paper_data['is_coi_pred'] or False,
                    is_fund_pred=paper_data['is_fund_pred'] or False,
                    is_register_pred=paper_data['is_register_pred'] or False,
                    is_replication=paper_data['is_replication'],
                    is_novelty=paper_data['is_novelty'],
                    transparency_score=paper_data['transparency_score'] or 0,
                    transparency_score_pct=paper_data['transparency_score_pct'] or 0.0,
                    assessment_date=assessment_date,
                    assessment_tool=paper_data['assessment_tool'] or '',
                    ost_version=paper_data['ost_version'] or '',
                )
                paper.save()
                papers_created += 1
        
        total_papers_imported += papers_created
        print(f"   📦 Chunk {chunk_num + 1}/{manifest['paper_chunks']}: {papers_created:,} created, {papers_skipped:,} skipped")
    
    print(f"\n✅ Import completed!")
    print(f"   - Total journals imported: {len(journals_data):,}")
    print(f"   - Total papers imported: {total_papers_imported:,}")
    
    # Final database statistics
    final_journals = Journal.objects.count()
    final_papers = Paper.objects.count()
    
    print(f"\n📊 Final Database Statistics:")
    print(f"   - Journals in database: {final_journals:,}")
    print(f"   - Papers in database: {final_papers:,}")
    print(f"   - Medical papers: {Paper.objects.exclude(broad_subject_category__in=['Dentistry', 'Orthodontics']).count():,}")
    print(f"   - Dental papers: {Paper.objects.filter(broad_subject_category__in=['Dentistry', 'Orthodontics']).count():,}")
    
    print(f"\n🎉 OST data successfully imported to Railway PostgreSQL!")

if __name__ == "__main__":
    import_data() 