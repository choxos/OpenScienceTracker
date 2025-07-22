#!/usr/bin/env python3
"""
Script to import all journals from comprehensive_journal_database.csv to the OST database.
This will enable proper journal matching for medical transparency data.
"""

import os
import sys
import django
import pandas as pd
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal


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
    import re
    year_clean = re.sub(r'[^\d]', '', str(year_str))
    
    if year_clean:
        try:
            year = int(year_clean)
            # Validate reasonable year range
            if 1800 <= year <= 2030:
                return year
        except ValueError:
            pass
    
    return None


def import_all_journals():
    """Import all journals from comprehensive_journal_database.csv"""
    print("📚 Importing All Journals from Comprehensive Database")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists('comprehensive_journal_database.csv'):
        print("❌ Error: comprehensive_journal_database.csv not found")
        print("💡 Run create_journal_database.py first to create the comprehensive database")
        return
    
    # Current journal count
    current_count = Journal.objects.count()
    print(f"📊 Current journals in database: {current_count:,}")
    
    # Load comprehensive journal data
    try:
        df = pd.read_csv('comprehensive_journal_database.csv', encoding='utf-8')
        print(f"📁 Comprehensive database loaded: {len(df):,} journals")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Statistics
    new_journals = 0
    updated_journals = 0
    errors = 0
    
    print(f"\n🔄 Processing journals...")
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"   Processing {idx:,}/{len(df):,} journals...")
        
        try:
            nlm_id = clean_text_field(row.get('nlm_id'))
            if not nlm_id:
                errors += 1
                continue
            
            # Check if journal already exists
            journal, created = Journal.objects.get_or_create(
                nlm_id=nlm_id,
                defaults={
                    'title_abbreviation': clean_text_field(row.get('title_abbreviation')) or 'Unknown',
                    'title_full': clean_text_field(row.get('title_full')) or '',
                    'authors': clean_text_field(row.get('title_other')) or '',
                    'indexing_status': clean_text_field(row.get('responsible_party')) or '',
                    'publication_start_year': clean_year_field(row.get('publication_start_year')),
                    'publication_end_year': clean_year_field(row.get('publication_end_year')),
                    'frequency': clean_text_field(row.get('frequency')) or '',
                    'country': clean_text_field(row.get('country')) or '',
                    'publisher': clean_text_field(row.get('publisher')) or '',
                    'language': clean_text_field(row.get('language')) or '',
                    'issn_electronic': clean_text_field(row.get('issn_electronic')),
                    'issn_print': clean_text_field(row.get('issn_print')),
                    'issn_linking': clean_text_field(row.get('issn_linking')),
                    'lccn': clean_text_field(row.get('lccn')),
                    'electronic_links': clean_text_field(row.get('url')) or '',
                    'publication_types': clean_text_field(row.get('medline_ta')) or '',
                    'notes': clean_text_field(row.get('nlm_unique_id')) or '',
                    'mesh_terms': clean_text_field(row.get('classification')) or '',
                    'broad_subject_terms': clean_text_field(row.get('broad_subject_terms')) or '',
                    'subject_term_count': int(row.get('subject_term_count', 0)) if pd.notna(row.get('subject_term_count')) else 0,
                }
            )
            
            if created:
                new_journals += 1
            else:
                # Update existing journal with comprehensive data if fields are empty
                updated = False
                if not journal.title_full and clean_text_field(row.get('title_full')):
                    journal.title_full = clean_text_field(row.get('title_full'))
                    updated = True
                if not journal.broad_subject_terms and clean_text_field(row.get('broad_subject_terms')):
                    journal.broad_subject_terms = clean_text_field(row.get('broad_subject_terms'))
                    updated = True
                if not journal.country and clean_text_field(row.get('country')):
                    journal.country = clean_text_field(row.get('country'))
                    updated = True
                if not journal.publisher and clean_text_field(row.get('publisher')):
                    journal.publisher = clean_text_field(row.get('publisher'))
                    updated = True
                if not journal.issn_electronic and clean_text_field(row.get('issn_electronic')):
                    journal.issn_electronic = clean_text_field(row.get('issn_electronic'))
                    updated = True
                if not journal.issn_print and clean_text_field(row.get('issn_print')):
                    journal.issn_print = clean_text_field(row.get('issn_print'))
                    updated = True
                if not journal.issn_linking and clean_text_field(row.get('issn_linking')):
                    journal.issn_linking = clean_text_field(row.get('issn_linking'))
                    updated = True
                if not journal.language and clean_text_field(row.get('language')):
                    journal.language = clean_text_field(row.get('language'))
                    updated = True
                if not journal.frequency and clean_text_field(row.get('frequency')):
                    journal.frequency = clean_text_field(row.get('frequency'))
                    updated = True
                    
                if updated:
                    journal.save()
                    updated_journals += 1
                    
        except Exception as e:
            print(f"   ⚠️  Error processing journal {idx}: {e}")
            errors += 1
    
    print(f"\n✅ Journal import completed!")
    print(f"📊 Final Statistics:")
    print(f"   - Total processed: {len(df):,}")
    print(f"   - New journals added: {new_journals:,}")
    print(f"   - Existing journals updated: {updated_journals:,}")
    print(f"   - Errors: {errors:,}")
    
    # Updated database statistics
    final_count = Journal.objects.count()
    print(f"\n📈 Database Statistics:")
    print(f"   - Previous journal count: {current_count:,}")
    print(f"   - Current journal count: {final_count:,}")
    print(f"   - Net increase: {final_count - current_count:,}")
    
    # Subject category statistics
    print(f"\n🏷️  Subject Category Distribution:")
    categories = Journal.objects.exclude(broad_subject_terms__isnull=True).exclude(broad_subject_terms='')
    category_counts = {}
    
    for journal in categories:
        if journal.broad_subject_terms:
            terms = journal.broad_subject_terms.split(';')
            for term in terms:
                term = term.strip()
                if term:
                    category_counts[term] = category_counts.get(term, 0) + 1
    
    # Show top 10 categories
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {category}: {count:,} journals")
    
    print(f"\n🎉 All journals imported! Ready for medical transparency data import.")


if __name__ == "__main__":
    import_all_journals() 