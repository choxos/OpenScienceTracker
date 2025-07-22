#!/usr/bin/env python3
"""
Script to import Europe PMC data from dental_transparency_db.csv and enhance existing papers.
This script will:
1. Load the Europe PMC data
2. Match papers by PMID/PMCID
3. Add Europe PMC metadata to existing papers
4. Match journal ISSNs to get broad subject categories
5. Update transparency scores to include Open Access indicator
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal


def clean_boolean_field(value):
    """Convert string boolean values to Python boolean"""
    if pd.isna(value) or value == "":
        return False
    if isinstance(value, str):
        return value.upper() in ['Y', 'YES', 'TRUE', '1']
    return bool(value)


def clean_date_field(date_str):
    """Convert date string to datetime.date object"""
    if pd.isna(date_str) or date_str == "":
        return None
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except:
        try:
            return datetime.strptime(str(date_str), '%Y-%m-%d %H:%M:%S').date()
        except:
            return None


def clean_text_field(value):
    """Clean text field values"""
    if pd.isna(value) or value == "":
        return None
    return str(value).strip()


def get_primary_subject_category(journal):
    """Get the primary broad subject category from journal's broad_subject_terms"""
    if not journal.broad_subject_terms:
        return None
    
    # Split by semicolon and take the first term
    terms = journal.broad_subject_terms.split(';')
    if terms:
        return terms[0].strip()
    return None


def match_issn_to_journals(journalIssn):
    """Match ISSN to journals in the database"""
    if not journalIssn:
        return None
    
    # Try to find journal by various ISSN fields
    journal = Journal.objects.filter(
        models.Q(issn_electronic=journalIssn) |
        models.Q(issn_print=journalIssn) |
        models.Q(issn_linking=journalIssn)
    ).first()
    
    return journal


def import_europe_pmc_data():
    """Main function to import and link Europe PMC data"""
    print("🔄 Loading Europe PMC data from dental_transparency_db.csv...")
    
    # Load the Europe PMC data
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                epmc_df = pd.read_csv('papers/dental_transparency_data_codes/data/dental_transparency_db.csv', 
                                    encoding=encoding)
                print(f"✅ Loaded {len(epmc_df)} records from Europe PMC data (encoding: {encoding})")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise Exception("Could not decode file with any common encoding")
    except Exception as e:
        print(f"❌ Error loading Europe PMC data: {e}")
        return
    
    # Display the columns to understand the structure
    print(f"📊 Columns in Europe PMC data: {list(epmc_df.columns)}")
    
    # Statistics
    matched_papers = 0
    updated_papers = 0
    new_open_access = 0
    categorized_papers = 0
    
    print("\n🔄 Processing papers and matching with existing database...")
    
    for idx, row in epmc_df.iterrows():
        if idx % 1000 == 0:
            print(f"   Processed {idx}/{len(epmc_df)} records...")
        
        pmid = clean_text_field(row.get('pmid'))
        pmcid = clean_text_field(row.get('pmcid'))
        
        if not pmid:
            continue
            
        # Try to find the paper in our database
        paper = None
        if pmid:
            paper = Paper.objects.filter(pmid=pmid).first()
        
        if not paper and pmcid:
            paper = Paper.objects.filter(pmcid=pmcid).first()
            
        if not paper:
            continue
            
        matched_papers += 1
        
        # Update paper with Europe PMC data
        updated = False
        
        # Add new fields from Europe PMC
        if row.get('issue') and not paper.issue:
            paper.issue = clean_text_field(row.get('issue'))
            updated = True
            
        if row.get('pageInfo') and not paper.page_info:
            paper.page_info = clean_text_field(row.get('pageInfo'))
            updated = True
            
        if row.get('journalVolume') and not paper.journal_volume:
            paper.journal_volume = clean_text_field(row.get('journalVolume'))
            updated = True
            
        if row.get('pubType') and not paper.pub_type:
            paper.pub_type = clean_text_field(row.get('pubType'))
            updated = True
            
        # Update Europe PMC availability flags
        is_open_access = clean_boolean_field(row.get('isOpenAccess'))
        if is_open_access and not paper.is_open_access:
            paper.is_open_access = True
            new_open_access += 1
            updated = True
            
        in_epmc = clean_boolean_field(row.get('inEPMC'))
        if in_epmc and not paper.in_epmc:
            paper.in_epmc = True
            updated = True
            
        in_pmc = clean_boolean_field(row.get('inPMC'))
        if in_pmc and not paper.in_pmc:
            paper.in_pmc = True
            updated = True
            
        has_pdf = clean_boolean_field(row.get('hasPDF'))
        if has_pdf and not paper.has_pdf:
            paper.has_pdf = True
            updated = True
            
        # Update first publication date if available and not set
        if row.get('firstPublicationDate') and not paper.first_publication_date:
            paper.first_publication_date = clean_date_field(row.get('firstPublicationDate'))
            if paper.first_publication_date:
                updated = True
        
        # Update journal ISSN if available and not set
        if row.get('journalIssn') and not paper.journal_issn:
            paper.journal_issn = clean_text_field(row.get('journalIssn'))
            updated = True
            
        # Get broad subject category from journal
        if not paper.broad_subject_category and paper.journal:
            category = get_primary_subject_category(paper.journal)
            if category:
                paper.broad_subject_category = category
                categorized_papers += 1
                updated = True
        
        # Recalculate transparency score with new Open Access indicator
        old_score = paper.transparency_score
        new_score = paper.calculate_transparency_score()
        if new_score != old_score:
            paper.transparency_score = new_score
            paper.transparency_score_pct = (new_score / 8.0) * 100  # Updated to 8 indicators
            updated = True
            
        if updated:
            paper.save()
            updated_papers += 1
    
    print(f"\n✅ Import completed!")
    print(f"📊 Statistics:")
    print(f"   - Total Europe PMC records: {len(epmc_df)}")
    print(f"   - Matched papers in database: {matched_papers}")
    print(f"   - Updated papers: {updated_papers}")
    print(f"   - New open access papers: {new_open_access}")
    print(f"   - Categorized papers: {categorized_papers}")
    
    # Additional statistics
    total_papers = Paper.objects.count()
    open_access_papers = Paper.objects.filter(is_open_access=True).count()
    categorized_total = Paper.objects.exclude(broad_subject_category__isnull=True).count()
    
    print(f"\n📈 Updated Database Statistics:")
    print(f"   - Total papers: {total_papers}")
    print(f"   - Open access papers: {open_access_papers} ({(open_access_papers/total_papers)*100:.1f}%)")
    print(f"   - Categorized papers: {categorized_total} ({(categorized_total/total_papers)*100:.1f}%)")
    
    # Show transparency indicator statistics
    print(f"\n🔍 Updated Transparency Indicators:")
    transparency_stats = {
        'Data Sharing': Paper.objects.filter(is_open_data=True).count(),
        'Code Sharing': Paper.objects.filter(is_open_code=True).count(),
        'COI Disclosure': Paper.objects.filter(is_coi_pred=True).count(),
        'Funding Disclosure': Paper.objects.filter(is_fund_pred=True).count(),
        'Protocol Registration': Paper.objects.filter(is_register_pred=True).count(),
        'Open Access': Paper.objects.filter(is_open_access=True).count(),
    }
    
    for indicator, count in transparency_stats.items():
        percentage = (count / total_papers) * 100
        print(f"   - {indicator}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    # Add missing import
    from django.db import models
    
    import_europe_pmc_data() 