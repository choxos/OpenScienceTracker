#!/usr/bin/env python3
"""
Script to import dental transparency data into the Django OST database.
This script loads data from the CSV files and populates the Django models.
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime, date
import numpy as np

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal, Paper, ResearchField, TransparencyTrend

def import_journals():
    """Import journals from comprehensive journal database"""
    print("Importing journals...")
    
    # Load comprehensive journal database
    journals_df = pd.read_csv('comprehensive_journal_database.csv')
    
    # Filter for dental journals
    dental_journals = journals_df[
        journals_df['broad_subject_terms'].str.contains('Dentistry|Orthodontics', na=False)
    ]
    
    print(f"Found {len(dental_journals)} dental journals to import")
    
    created_count = 0
    updated_count = 0
    
    for _, row in dental_journals.iterrows():
        # Create or update journal
        journal_data = {
            'nlm_id': row.get('nlm_id'),
            'title_abbreviation': row.get('title_abbreviation', ''),
            'title_full': row.get('title_full', ''),
            'authors': row.get('authors'),
            'publication_start_year': row.get('publication_start_year') if pd.notna(row.get('publication_start_year')) else None,
            'publication_end_year': row.get('publication_end_year') if pd.notna(row.get('publication_end_year')) else None,
            'frequency': row.get('frequency'),
            'country': row.get('country'),
            'publisher': row.get('publisher'),
            'language': row.get('language'),
            'issn_electronic': row.get('issn_electronic'),
            'issn_print': row.get('issn_print'),
            'issn_linking': row.get('issn_linking'),
            'indexing_status': row.get('indexing_status'),
            'broad_subject_terms': row.get('broad_subject_terms', ''),
            'subject_term_count': row.get('subject_term_count', 1),
            'mesh_terms': row.get('mesh_terms'),
            'lccn': row.get('lccn'),
            'electronic_links': row.get('electronic_links'),
            'publication_types': row.get('publication_types'),
            'notes': row.get('notes'),
        }
        
        # Clean data
        for key, value in journal_data.items():
            if pd.isna(value) or value == 'nan':
                journal_data[key] = None
        
        try:
            journal, created = Journal.objects.get_or_create(
                title_abbreviation=journal_data['title_abbreviation'],
                defaults=journal_data
            )
            
            if created:
                created_count += 1
            else:
                # Update existing journal
                for key, value in journal_data.items():
                    if value is not None:
                        setattr(journal, key, value)
                journal.save()
                updated_count += 1
                
        except Exception as e:
            print(f"Error importing journal {journal_data['title_abbreviation']}: {e}")
            continue
    
    print(f"Journals import complete: {created_count} created, {updated_count} updated")
    return created_count + updated_count

def import_papers():
    """Import papers from dental transparency database"""
    print("Importing papers...")
    
    # Load dental OST database
    papers_df = pd.read_csv('dental_ost_database.csv')
    
    print(f"Found {len(papers_df)} papers to import")
    
    created_count = 0
    updated_count = 0
    errors = 0
    
    # Create journal mapping
    journal_mapping = {}
    for journal in Journal.objects.all():
        journal_mapping[journal.title_abbreviation] = journal
    
    for idx, row in papers_df.iterrows():
        if idx % 1000 == 0:
            print(f"Processing paper {idx}/{len(papers_df)}")
        
        # Find journal
        journal_title = row.get('journalTitle', '')
        journal = journal_mapping.get(journal_title)
        
        if not journal:
            # Try to create journal if not found
            try:
                journal = Journal.objects.create(
                    title_abbreviation=journal_title,
                    title_full=journal_title,
                    broad_subject_terms='Dentistry'
                )
                journal_mapping[journal_title] = journal
            except Exception as e:
                print(f"Could not create journal {journal_title}: {e}")
                errors += 1
                continue
        
        # Parse dates
        first_pub_date = None
        if pd.notna(row.get('firstPublicationDate')):
            try:
                first_pub_date = datetime.strptime(row['firstPublicationDate'], '%Y-%m-%d').date()
            except:
                pass
        
        assessment_date = None
        if pd.notna(row.get('assessment_date')):
            try:
                assessment_date = datetime.fromisoformat(row['assessment_date'].replace('Z', '+00:00'))
            except:
                pass
        
        # Create paper data
        paper_data = {
            'pmid': str(row.get('pmid', '')),
            'pmcid': row.get('pmcid'),
            'doi': row.get('doi'),
            'title': row.get('title', ''),
            'author_string': row.get('authorString', ''),
            'journal': journal,
            'journal_title': journal_title,
            'pub_year': int(row.get('pubYear_modified', row.get('year_firstpub', 2000))),
            'pub_year_modified': row.get('pubYear_modified'),
            'first_publication_date': first_pub_date,
            'year_first_pub': row.get('year_firstpub') if pd.notna(row.get('year_firstpub')) else None,
            'month_first_pub': row.get('month_firstpub') if pd.notna(row.get('month_firstpub')) else None,
            'journal_issn': row.get('journalIssn'),
            'jif2020': row.get('jif2020') if pd.notna(row.get('jif2020')) else None,
            'scimago_publisher': row.get('scimago_publisher'),
            
            # Transparency indicators
            'is_open_data': bool(row.get('is_open_data', False)),
            'is_open_code': bool(row.get('is_open_code', False)),
            'is_coi_pred': bool(row.get('is_coi_pred', False)),
            'is_fund_pred': bool(row.get('is_fund_pred', False)),
            'is_register_pred': bool(row.get('is_register_pred', False)),
            'is_replication': row.get('is_replication') if pd.notna(row.get('is_replication')) else None,
            'is_novelty': row.get('is_novelty') if pd.notna(row.get('is_novelty')) else None,
            
            # Disclosure indicators
            'disc_data': bool(row.get('disc_data', False)),
            'disc_code': bool(row.get('disc_code', False)),
            'disc_coi': bool(row.get('disc_coi', False)),
            'disc_fund': bool(row.get('disc_fund', False)),
            'disc_register': bool(row.get('disc_register', False)),
            'disc_replication': row.get('disc_replication') if pd.notna(row.get('disc_replication')) else None,
            'disc_novelty': row.get('disc_novelty') if pd.notna(row.get('disc_novelty')) else None,
            
            # Metadata
            'assessment_date': assessment_date,
            'assessment_tool': row.get('assessment_tool', 'rtransparent'),
            'ost_version': row.get('ost_version', '1.0'),
        }
        
        # Clean data
        for key, value in paper_data.items():
            if pd.isna(value) or value == 'nan':
                if key in ['is_replication', 'is_novelty', 'disc_replication', 'disc_novelty']:
                    paper_data[key] = None
                elif key in ['pmid', 'title', 'author_string']:
                    paper_data[key] = ''
                else:
                    paper_data[key] = None
        
        try:
            paper, created = Paper.objects.get_or_create(
                pmid=paper_data['pmid'],
                defaults=paper_data
            )
            
            if created:
                created_count += 1
            else:
                # Update existing paper
                for key, value in paper_data.items():
                    if key != 'pmid' and value is not None:
                        setattr(paper, key, value)
                paper.save()
                updated_count += 1
                
        except Exception as e:
            print(f"Error importing paper {paper_data['pmid']}: {e}")
            errors += 1
            continue
    
    print(f"Papers import complete: {created_count} created, {updated_count} updated, {errors} errors")
    return created_count + updated_count

def create_research_fields():
    """Create research fields from broad subject terms"""
    print("Creating research fields...")
    
    # Define major research fields
    fields = [
        ('Dentistry', 'General dentistry and oral health'),
        ('Orthodontics', 'Orthodontic treatment and research'),
        ('Medicine', 'General medical research'),
        ('Surgery', 'Surgical procedures and research'),
        ('Cardiology', 'Heart and cardiovascular research'),
        ('Neurology', 'Neurological research and treatment'),
        ('Pediatrics', 'Child health and development'),
        ('Psychiatry', 'Mental health research'),
        ('Public Health', 'Population health and epidemiology'),
        ('Pharmacology', 'Drug development and therapy'),
    ]
    
    created_count = 0
    for name, description in fields:
        field, created = ResearchField.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        if created:
            created_count += 1
    
    print(f"Research fields created: {created_count}")
    return created_count

def update_journal_statistics():
    """Update journal statistics based on papers"""
    print("Updating journal statistics...")
    
    journals = Journal.objects.all()
    for journal in journals:
        papers = journal.papers.all()
        # Statistics will be calculated automatically through annotations in views
        pass
    
    print("Journal statistics updated")

def main():
    """Main import function"""
    print("Starting OST data import...")
    print(f"Time: {datetime.now()}")
    
    try:
        # Import data
        journal_count = import_journals()
        field_count = create_research_fields()
        paper_count = import_papers()
        update_journal_statistics()
        
        print("\n" + "="*50)
        print("IMPORT SUMMARY")
        print("="*50)
        print(f"Journals: {journal_count}")
        print(f"Research Fields: {field_count}")
        print(f"Papers: {paper_count}")
        print(f"Time completed: {datetime.now()}")
        print("="*50)
        
    except Exception as e:
        print(f"Import failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 