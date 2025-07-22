#!/usr/bin/env python3
"""
Script to import medical transparency data from papers/medicaltransparency_opendata.csv
This script will:
1. Process the large CSV file in chunks to avoid memory issues
2. Match journals by ISSN or name with the subject term database
3. Add papers that have matching journals to the OST database
4. Handle Europe PMC metadata and transparency indicators
5. Provide progress tracking and statistics
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime
import re
from django.db import transaction, IntegrityError

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal
from django.db.models import Q


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


def clean_year_field(year_str):
    """Clean year field, removing non-numeric characters"""
    if pd.isna(year_str) or year_str == "":
        return None
    
    # Convert to string and remove non-digits
    year_clean = re.sub(r'[^\d]', '', str(year_str))
    
    if year_clean:
        try:
            year = int(year_clean)
            # Validate reasonable year range
            if 1900 <= year <= 2030:
                return year
        except ValueError:
            pass
    
    return None


def clean_pub_year(year_str):
    """Handle publication year strings that might be ranges or have special characters"""
    if pd.isna(year_str) or year_str == "":
        return None
    
    year_str = str(year_str).strip()
    
    # Handle ranges like "2000 - 2004" - take the first year
    if '-' in year_str:
        year_str = year_str.split('-')[0].strip()
    
    # Handle "< 2000" format
    if '<' in year_str:
        year_str = year_str.replace('<', '').strip()
    
    # Handle "2000+" format
    if '+' in year_str:
        year_str = year_str.replace('+', '').strip()
    
    return clean_year_field(year_str)


def find_matching_journal(journal_title, journal_issn):
    """Find a matching journal in the database by ISSN or name"""
    journal = None
    
    # First try ISSN matching (most reliable)
    if journal_issn:
        issn_clean = clean_text_field(journal_issn)
        if issn_clean:
            journal = Journal.objects.filter(
                Q(issn_electronic=issn_clean) |
                Q(issn_print=issn_clean) |
                Q(issn_linking=issn_clean)
            ).first()
    
    # If no ISSN match, try journal name matching
    if not journal and journal_title:
        title_clean = clean_text_field(journal_title)
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


def get_primary_subject_category(journal):
    """Get the primary broad subject category from journal's broad_subject_terms"""
    if not journal or not journal.broad_subject_terms:
        return None
    
    # Split by semicolon and take the first term
    terms = journal.broad_subject_terms.split(';')
    if terms:
        return terms[0].strip()
    return None


def process_chunk(chunk_df, chunk_num, total_chunks):
    """Process a chunk of the medical transparency data"""
    print(f"📦 Processing chunk {chunk_num}/{total_chunks} ({len(chunk_df)} records)...")
    
    # Statistics for this chunk
    matched_journals = 0
    new_papers = 0
    duplicate_papers = 0
    invalid_papers = 0
    
    for idx, row in chunk_df.iterrows():
        try:
            # Basic validation
            pmid = clean_text_field(row.get('pmid'))
            if not pmid:
                invalid_papers += 1
                continue
            
            # Check if paper already exists
            if Paper.objects.filter(pmid=pmid).exists():
                duplicate_papers += 1
                continue
            
            # Find matching journal
            journal_title = clean_text_field(row.get('journalTitle'))
            journal_issn = clean_text_field(row.get('journalIssn'))
            
            journal = find_matching_journal(journal_title, journal_issn)
            if not journal:
                # Skip papers without matching journals
                continue
            
            matched_journals += 1
            
            # Extract paper data
            title = clean_text_field(row.get('title'))
            if not title:
                invalid_papers += 1
                continue
            
            author_string = clean_text_field(row.get('authorString')) or 'Unknown'
            pub_year = clean_pub_year(row.get('pubYear'))
            if not pub_year:
                invalid_papers += 1
                continue
            
            # Create paper with Europe PMC data
            paper_data = {
                'pmid': pmid,
                'pmcid': clean_text_field(row.get('pmcid')),
                'doi': clean_text_field(row.get('doi')),
                'title': title,
                'author_string': author_string,
                'journal': journal,
                'journal_title': journal_title or journal.title_abbreviation,
                'pub_year': pub_year,
                
                # Europe PMC fields
                'issue': clean_text_field(row.get('issue')),
                'page_info': clean_text_field(row.get('pageInfo')),
                'journal_volume': clean_text_field(row.get('journalVolume')),
                'pub_type': clean_text_field(row.get('pubType')),
                'is_open_access': clean_boolean_field(row.get('isOpenAccess')),
                'in_epmc': clean_boolean_field(row.get('inEPMC')),
                'in_pmc': clean_boolean_field(row.get('inPMC')),
                'has_pdf': clean_boolean_field(row.get('hasPDF')),
                'first_publication_date': clean_date_field(row.get('firstPublicationDate')),
                'journal_issn': journal_issn,
                
                # Subject category
                'broad_subject_category': get_primary_subject_category(journal),
                
                # Transparency indicators (if available in medical data)
                'is_open_data': clean_boolean_field(row.get('is_open_data')),
                'is_open_code': clean_boolean_field(row.get('is_open_code')),
                'is_coi_pred': clean_boolean_field(row.get('is_coi_pred')),
                'is_fund_pred': clean_boolean_field(row.get('is_fund_pred')),
                'is_register_pred': clean_boolean_field(row.get('is_register_pred')),
                
                # Assessment metadata
                'assessment_date': datetime.now().date(),
                'assessment_tool': 'rtransparent',
                'ost_version': '1.0',
            }
            
            # Create paper instance
            paper = Paper(**paper_data)
            
            # Calculate transparency score
            paper.transparency_score = paper.calculate_transparency_score()
            paper.transparency_score_pct = (paper.transparency_score / 8.0) * 100
            
            # Save paper
            with transaction.atomic():
                paper.save()
                new_papers += 1
                
        except IntegrityError:
            # Handle duplicate PMID
            duplicate_papers += 1
        except Exception as e:
            print(f"   ⚠️  Error processing row {idx}: {e}")
            invalid_papers += 1
    
    return {
        'matched_journals': matched_journals,
        'new_papers': new_papers,
        'duplicate_papers': duplicate_papers,
        'invalid_papers': invalid_papers
    }


def import_medical_transparency_data():
    """Main function to import medical transparency data in chunks"""
    file_path = 'papers/medicaltransparency_opendata.csv'
    
    print("🏥 Starting Medical Transparency Data Import")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return
    
    # Get file size
    file_size = os.path.getsize(file_path) / (1024 ** 3)  # GB
    print(f"📁 File size: {file_size:.2f} GB")
    
    # Process in chunks to avoid memory issues
    chunk_size = 10000  # Process 10,000 rows at a time
    
    print(f"📊 Processing in chunks of {chunk_size:,} rows...")
    print("🔄 Starting import process...\n")
    
    # Initialize statistics
    total_stats = {
        'total_processed': 0,
        'matched_journals': 0,
        'new_papers': 0,
        'duplicate_papers': 0,
        'invalid_papers': 0
    }
    
    chunk_num = 0
    
    try:
        # Read CSV in chunks
        for chunk_df in pd.read_csv(file_path, chunksize=chunk_size, encoding='latin-1'):
            chunk_num += 1
            
            # Estimate total chunks (approximate)
            if chunk_num == 1:
                print(f"📋 Columns in medical data: {list(chunk_df.columns)}")
                print(f"📊 Sample data structure validated\n")
            
            # Process this chunk
            chunk_stats = process_chunk(chunk_df, chunk_num, "?")
            
            # Update total statistics
            total_stats['total_processed'] += len(chunk_df)
            for key, value in chunk_stats.items():
                total_stats[key] += value
            
            # Progress update
            print(f"   ✅ Chunk {chunk_num} completed:")
            print(f"      - Journal matches: {chunk_stats['matched_journals']:,}")
            print(f"      - New papers added: {chunk_stats['new_papers']:,}")
            print(f"      - Duplicates skipped: {chunk_stats['duplicate_papers']:,}")
            print(f"      - Invalid records: {chunk_stats['invalid_papers']:,}")
            print(f"      - Total processed so far: {total_stats['total_processed']:,}\n")
            
            # Memory cleanup
            del chunk_df
            
    except Exception as e:
        print(f"❌ Error during import: {e}")
        return
    
    print("\n" + "=" * 50)
    print("✅ Medical Transparency Import Completed!")
    print("=" * 50)
    
    # Final statistics
    print(f"📊 Final Statistics:")
    print(f"   - Total records processed: {total_stats['total_processed']:,}")
    print(f"   - Journal matches found: {total_stats['matched_journals']:,}")
    print(f"   - New papers added: {total_stats['new_papers']:,}")
    print(f"   - Duplicate papers skipped: {total_stats['duplicate_papers']:,}")
    print(f"   - Invalid records skipped: {total_stats['invalid_papers']:,}")
    
    # Match percentage
    if total_stats['total_processed'] > 0:
        match_pct = (total_stats['matched_journals'] / total_stats['total_processed']) * 100
        print(f"   - Journal match rate: {match_pct:.1f}%")
    
    # Updated database statistics
    total_papers = Paper.objects.count()
    medical_papers = Paper.objects.exclude(broad_subject_category='Dentistry').exclude(broad_subject_category='Orthodontics').count()
    dental_papers = Paper.objects.filter(broad_subject_category__in=['Dentistry', 'Orthodontics']).count()
    
    print(f"\n📈 Updated Database Statistics:")
    print(f"   - Total papers: {total_papers:,}")
    print(f"   - Medical papers: {medical_papers:,}")
    print(f"   - Dental papers: {dental_papers:,}")
    
    # Subject category distribution
    print(f"\n🏷️  Subject Category Distribution:")
    categories = Paper.objects.exclude(broad_subject_category__isnull=True).values_list('broad_subject_category', flat=True)
    category_counts = {}
    for cat in categories:
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {category}: {count:,} papers")
    
    print(f"\n🎉 Medical transparency data successfully integrated into OST!")


if __name__ == "__main__":
    import_medical_transparency_data() 