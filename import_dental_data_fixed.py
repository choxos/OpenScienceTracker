#!/usr/bin/env python3
"""
Fixed script to import dental transparency data into the Django OST database.
This version handles data type conversion issues properly.
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime, date
import numpy as np
import re

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal, Paper, ResearchField, TransparencyTrend

def clean_year_field(year_str):
    """Clean year fields that may contain 'u' characters or invalid data"""
    if pd.isna(year_str) or year_str == '' or year_str == 'nan':
        return None
    
    year_str = str(year_str)
    
    # Remove 'u' characters and other non-digits
    year_clean = re.sub(r'[^\d]', '', year_str)
    
    if not year_clean:
        return None
    
    try:
        year = int(year_clean)
        # Validate reasonable year range
        if 1800 <= year <= 2030:
            return year
        else:
            return None
    except ValueError:
        return None

def clean_pub_year(year_str):
    """Clean publication year that might be a range like '2000 - 2004'"""
    if pd.isna(year_str) or year_str == '' or year_str == 'nan':
        return 2000  # Default year
    
    year_str = str(year_str).strip()
    
    # Handle year ranges - take the first year
    if ' - ' in year_str:
        year_str = year_str.split(' - ')[0]
    elif '-' in year_str:
        year_str = year_str.split('-')[0]
    
    # Handle cases like "< 2000"
    if '<' in year_str:
        year_str = year_str.replace('<', '').strip()
    
    try:
        year = int(year_str)
        if 1900 <= year <= 2030:
            return year
        else:
            return 2000
    except ValueError:
        return 2000

def import_journals():
    """Import journals from comprehensive journal database with better error handling"""
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
    error_count = 0
    
    for _, row in dental_journals.iterrows():
        # Skip if no title abbreviation
        if pd.isna(row.get('title_abbreviation')) or row.get('title_abbreviation') == '':
            error_count += 1
            continue
        
        # Create journal data with proper cleaning
        journal_data = {
            'nlm_id': str(row.get('nlm_id')) if pd.notna(row.get('nlm_id')) else None,
            'title_abbreviation': str(row.get('title_abbreviation', '')),
            'title_full': str(row.get('title_full', '')),
            'authors': str(row.get('authors')) if pd.notna(row.get('authors')) else None,
            'publication_start_year': clean_year_field(row.get('publication_start_year')),
            'publication_end_year': clean_year_field(row.get('publication_end_year')),
            'frequency': str(row.get('frequency')) if pd.notna(row.get('frequency')) else None,
            'country': str(row.get('country')) if pd.notna(row.get('country')) else None,
            'publisher': str(row.get('publisher')) if pd.notna(row.get('publisher')) else None,
            'language': str(row.get('language')) if pd.notna(row.get('language')) else None,
            'issn_electronic': str(row.get('issn_electronic')) if pd.notna(row.get('issn_electronic')) else None,
            'issn_print': str(row.get('issn_print')) if pd.notna(row.get('issn_print')) else None,
            'issn_linking': str(row.get('issn_linking')) if pd.notna(row.get('issn_linking')) else None,
            'indexing_status': str(row.get('indexing_status')) if pd.notna(row.get('indexing_status')) else None,
            'broad_subject_terms': str(row.get('broad_subject_terms', '')),
            'subject_term_count': int(row.get('subject_term_count', 1)) if pd.notna(row.get('subject_term_count')) else 1,
            'mesh_terms': str(row.get('mesh_terms')) if pd.notna(row.get('mesh_terms')) else None,
            'lccn': str(row.get('lccn')) if pd.notna(row.get('lccn')) else None,
            'electronic_links': str(row.get('electronic_links')) if pd.notna(row.get('electronic_links')) else None,
            'publication_types': str(row.get('publication_types')) if pd.notna(row.get('publication_types')) else None,
            'notes': str(row.get('notes')) if pd.notna(row.get('notes')) else None,
        }
        
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
            error_count += 1
            continue
    
    print(f"Journals import complete: {created_count} created, {updated_count} updated, {error_count} errors")
    return created_count + updated_count

def import_papers():
    """Import papers from dental transparency database with better error handling"""
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
        
        # Skip if no PMID
        pmid = str(row.get('pmid', ''))
        if not pmid or pmid == 'nan':
            errors += 1
            continue
        
        # Find journal
        journal_title = str(row.get('journalTitle', ''))
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
                errors += 1
                continue
        
        # Parse dates
        first_pub_date = None
        if pd.notna(row.get('firstPublicationDate')):
            try:
                first_pub_date = datetime.strptime(str(row['firstPublicationDate']), '%Y-%m-%d').date()
            except:
                pass
        
        assessment_date = None
        if pd.notna(row.get('assessment_date')):
            try:
                assessment_date = datetime.fromisoformat(str(row['assessment_date']).replace('Z', '+00:00'))
            except:
                pass
        
        # Create paper data with proper type handling
        paper_data = {
            'pmid': pmid,
            'pmcid': str(row.get('pmcid')) if pd.notna(row.get('pmcid')) else None,
            'doi': str(row.get('doi')) if pd.notna(row.get('doi')) else None,
            'title': str(row.get('title', '')),
            'author_string': str(row.get('authorString', '')),
            'journal': journal,
            'journal_title': journal_title,
            'pub_year': clean_pub_year(row.get('pubYear_modified', row.get('year_firstpub', 2000))),
            'pub_year_modified': str(row.get('pubYear_modified')) if pd.notna(row.get('pubYear_modified')) else None,
            'first_publication_date': first_pub_date,
            'year_first_pub': clean_year_field(row.get('year_firstpub')),
            'month_first_pub': int(row.get('month_firstpub')) if pd.notna(row.get('month_firstpub')) else None,
            'journal_issn': str(row.get('journalIssn')) if pd.notna(row.get('journalIssn')) else None,
            'jif2020': float(row.get('jif2020')) if pd.notna(row.get('jif2020')) else None,
            'scimago_publisher': str(row.get('scimago_publisher')) if pd.notna(row.get('scimago_publisher')) else None,
            
            # Transparency indicators (handle different boolean representations)
            'is_open_data': bool(row.get('is_open_data', False)) if pd.notna(row.get('is_open_data')) else False,
            'is_open_code': bool(row.get('is_open_code', False)) if pd.notna(row.get('is_open_code')) else False,
            'is_coi_pred': bool(row.get('is_coi_pred', False)) if pd.notna(row.get('is_coi_pred')) else False,
            'is_fund_pred': bool(row.get('is_fund_pred', False)) if pd.notna(row.get('is_fund_pred')) else False,
            'is_register_pred': bool(row.get('is_register_pred', False)) if pd.notna(row.get('is_register_pred')) else False,
            'is_replication': None,  # Not available in current data
            'is_novelty': None,      # Not available in current data
            
            # Disclosure indicators
            'disc_data': bool(row.get('disc_data', False)) if pd.notna(row.get('disc_data')) else False,
            'disc_code': bool(row.get('disc_code', False)) if pd.notna(row.get('disc_code')) else False,
            'disc_coi': bool(row.get('disc_coi', False)) if pd.notna(row.get('disc_coi')) else False,
            'disc_fund': bool(row.get('disc_fund', False)) if pd.notna(row.get('disc_fund')) else False,
            'disc_register': bool(row.get('disc_register', False)) if pd.notna(row.get('disc_register')) else False,
            'disc_replication': None,
            'disc_novelty': None,
            
            # Metadata
            'assessment_date': assessment_date,
            'assessment_tool': str(row.get('assessment_tool', 'rtransparent')),
            'ost_version': str(row.get('ost_version', '1.0')),
        }
        
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

def main():
    """Main import function"""
    print("Starting OST data import (fixed version)...")
    print(f"Time: {datetime.now()}")
    
    try:
        # Import data
        journal_count = import_journals()
        field_count = create_research_fields()
        paper_count = import_papers()
        
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