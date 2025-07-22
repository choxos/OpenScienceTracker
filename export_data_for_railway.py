#!/usr/bin/env python3
"""
Export all OST data to JSON files for Railway PostgreSQL import
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal

def export_data():
    """Export all data to JSON files"""
    print("📦 Exporting OST Data for Railway Deployment")
    print("=" * 50)
    
    # Create export directory
    os.makedirs('railway_data', exist_ok=True)
    
    # Export journals
    print("📚 Exporting journals...")
    journals = []
    for journal in Journal.objects.all():
        journals.append({
            'nlm_id': journal.nlm_id,
            'title_abbreviation': journal.title_abbreviation,
            'title_full': journal.title_full,
            'authors': journal.authors,
            'publication_start_year': journal.publication_start_year,
            'publication_end_year': journal.publication_end_year,
            'frequency': journal.frequency,
            'country': journal.country,
            'publisher': journal.publisher,
            'language': journal.language,
            'issn_electronic': journal.issn_electronic,
            'issn_print': journal.issn_print,
            'issn_linking': journal.issn_linking,
            'indexing_status': journal.indexing_status,
            'broad_subject_terms': journal.broad_subject_terms,
            'subject_term_count': journal.subject_term_count,
            'mesh_terms': journal.mesh_terms,
            'lccn': journal.lccn,
            'electronic_links': journal.electronic_links,
            'publication_types': journal.publication_types,
            'notes': journal.notes,
        })
    
    with open('railway_data/journals.json', 'w', encoding='utf-8') as f:
        json.dump(journals, f, indent=2, default=str)
    
    print(f"   ✅ Exported {len(journals):,} journals")
    
    # Export papers in chunks to avoid memory issues
    print("📄 Exporting papers...")
    papers_count = Paper.objects.count()
    chunk_size = 10000
    total_chunks = (papers_count + chunk_size - 1) // chunk_size
    
    for chunk_num in range(total_chunks):
        start_idx = chunk_num * chunk_size
        papers_chunk = Paper.objects.all()[start_idx:start_idx + chunk_size]
        
        papers = []
        for paper in papers_chunk:
            papers.append({
                'pmid': paper.pmid,
                'pmcid': paper.pmcid,
                'doi': paper.doi,
                'title': paper.title,
                'author_string': paper.author_string,
                'journal_nlm_id': paper.journal.nlm_id if paper.journal else None,
                'journal_title': paper.journal_title,
                'pub_year': paper.pub_year,
                'issue': paper.issue,
                'page_info': paper.page_info,
                'journal_volume': paper.journal_volume,
                'pub_type': paper.pub_type,
                'is_open_access': paper.is_open_access,
                'in_epmc': paper.in_epmc,
                'in_pmc': paper.in_pmc,
                'has_pdf': paper.has_pdf,
                'first_publication_date': paper.first_publication_date.isoformat() if paper.first_publication_date else None,
                'journal_issn': paper.journal_issn,
                'broad_subject_category': paper.broad_subject_category,
                'is_open_data': paper.is_open_data,
                'is_open_code': paper.is_open_code,
                'is_coi_pred': paper.is_coi_pred,
                'is_fund_pred': paper.is_fund_pred,
                'is_register_pred': paper.is_register_pred,
                'is_replication': paper.is_replication,
                'is_novelty': paper.is_novelty,
                'transparency_score': paper.transparency_score,
                'transparency_score_pct': paper.transparency_score_pct,
                'assessment_date': paper.assessment_date.isoformat() if paper.assessment_date else None,
                'assessment_tool': paper.assessment_tool,
                'ost_version': paper.ost_version,
            })
        
        filename = f'railway_data/papers_chunk_{chunk_num + 1:03d}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2, default=str)
        
        print(f"   📦 Exported chunk {chunk_num + 1}/{total_chunks} ({len(papers)} papers)")
    
    print(f"\n✅ Export completed!")
    print(f"   - Total journals: {len(journals):,}")
    print(f"   - Total papers: {papers_count:,}")
    print(f"   - Paper chunks: {total_chunks}")
    print(f"   - Files created in: railway_data/")
    
    # Create manifest
    manifest = {
        'export_date': datetime.now().isoformat(),
        'total_journals': len(journals),
        'total_papers': papers_count,
        'paper_chunks': total_chunks,
        'chunk_size': chunk_size,
        'files': {
            'journals': 'journals.json',
            'papers': [f'papers_chunk_{i+1:03d}.json' for i in range(total_chunks)]
        }
    }
    
    with open('railway_data/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"   📋 Manifest created: railway_data/manifest.json")

if __name__ == "__main__":
    export_data() 