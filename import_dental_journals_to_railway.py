#!/usr/bin/env python3
"""
Import dental journals from dental_journals_ost.csv to Railway PostgreSQL database
This script adds dental-specific journals to the existing Railway database
"""

import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Journal, ResearchField

def clean_text_field(value):
    """Clean text field for database storage"""
    if pd.isna(value) or value == "" or value == "nan":
        return ""
    return str(value).strip()

def clean_year_field(value):
    """Clean year field for database storage"""
    if pd.isna(value) or value == "" or value == "nan":
        return None
    try:
        year = int(float(value))
        if 1800 <= year <= 2030:  # Reasonable year range
            return year
    except (ValueError, TypeError):
        pass
    return None

def clean_number_field(value):
    """Clean numeric field for database storage"""
    if pd.isna(value) or value == "" or value == "nan":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def import_dental_journals():
    """Import dental journals from CSV file"""
    print("🦷 Importing Dental Journals to Railway Database")
    print("=" * 60)
    
    csv_file = 'dental_journals_ost.csv'
    if not os.path.exists(csv_file):
        print(f"❌ Error: {csv_file} not found")
        print("Please ensure the dental journals CSV file is in the project root")
        return False
    
    # Load the CSV file
    print(f"📄 Loading {csv_file}...")
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"   ✅ Loaded {len(df):,} dental journal records")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return False
    
    # Show sample data
    print(f"\n📊 Sample columns: {list(df.columns)[:5]}...")
    print(f"📊 Sample data:")
    print(df.head(2)[['title_abbreviation', 'title_full', 'country']].to_string())
    
    # Check database connection
    try:
        current_journal_count = Journal.objects.count()
        print(f"\n📚 Current journals in database: {current_journal_count:,}")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("Make sure you're connected to Railway database")
        return False
    
    # Import journals
    print(f"\n🔄 Processing dental journals...")
    created_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        with transaction.atomic():
            for idx, row in df.iterrows():
                if idx % 100 == 0:
                    print(f"   Processing {idx:,}/{len(df):,} journals...")
                
                try:
                    # Extract and clean data
                    nlm_id = clean_text_field(row.get('nlm_id'))
                    if not nlm_id or nlm_id == "":
                        print(f"   ⚠️  Skipping row {idx}: No NLM ID")
                        error_count += 1
                        continue
                    
                    title_abbreviation = clean_text_field(row.get('title_abbreviation')) or 'Unknown'
                    title_full = clean_text_field(row.get('title_full'))
                    
                    # Create or update journal
                    journal, created = Journal.objects.get_or_create(
                        nlm_id=nlm_id,
                        defaults={
                            'title_abbreviation': title_abbreviation,
                            'title_full': title_full,
                            'authors': clean_text_field(row.get('authors')),
                            'publication_start_year': clean_year_field(row.get('publication_start_year')),
                            'publication_end_year': clean_year_field(row.get('publication_end_year')),
                            'frequency': clean_text_field(row.get('frequency')),
                            'country': clean_text_field(row.get('country')),
                            'publisher': clean_text_field(row.get('publisher')),
                            'language': clean_text_field(row.get('language')),
                            'issn_electronic': clean_text_field(row.get('issn_electronic')),
                            'issn_print': clean_text_field(row.get('issn_print')),
                            'issn_linking': clean_text_field(row.get('issn_linking')),
                            'lccn': clean_text_field(row.get('lccn')),
                            'electronic_links': clean_text_field(row.get('electronic_links')),
                            'indexing_status': clean_text_field(row.get('indexing_status')),
                            'mesh_terms': clean_text_field(row.get('mesh_terms')),
                            'publication_types': clean_text_field(row.get('publication_types')),
                            'notes': clean_text_field(row.get('notes')),
                            'broad_subject_terms': clean_text_field(row.get('broad_subject_terms')),
                            'subject_term_count': clean_number_field(row.get('subject_term_count')) or 1,
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Update existing journal with any missing data
                        updated = False
                        
                        # Update fields that might be missing
                        if not journal.title_full and title_full:
                            journal.title_full = title_full
                            updated = True
                        
                        if not journal.country and clean_text_field(row.get('country')):
                            journal.country = clean_text_field(row.get('country'))
                            updated = True
                        
                        if not journal.publisher and clean_text_field(row.get('publisher')):
                            journal.publisher = clean_text_field(row.get('publisher'))
                            updated = True
                        
                        if not journal.broad_subject_terms and clean_text_field(row.get('broad_subject_terms')):
                            journal.broad_subject_terms = clean_text_field(row.get('broad_subject_terms'))
                            updated = True
                        
                        if updated:
                            journal.save()
                            updated_count += 1
                
                except Exception as e:
                    print(f"   ⚠️  Error processing row {idx}: {e}")
                    error_count += 1
                    continue
        
        print(f"\n✅ Dental journals import completed!")
        print(f"📊 Import Statistics:")
        print(f"   - Total processed: {len(df):,}")
        print(f"   - New journals created: {created_count:,}")
        print(f"   - Existing journals updated: {updated_count:,}")
        print(f"   - Errors: {error_count:,}")
        
        # Updated database statistics
        final_count = Journal.objects.count()
        print(f"\n📈 Database Statistics:")
        print(f"   - Previous journal count: {current_journal_count:,}")
        print(f"   - Current journal count: {final_count:,}")
        print(f"   - Net increase: {final_count - current_journal_count:,}")
        
        # Check dental journals specifically
        dental_journals = Journal.objects.filter(
            broad_subject_terms__icontains='Dentistry'
        ).count()
        print(f"   - Total dental journals: {dental_journals:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Critical error during import: {e}")
        return False

def update_research_fields():
    """Update research fields after importing dental journals"""
    print(f"\n🔄 Updating research fields...")
    
    # Ensure 'Dentistry' field exists and has correct statistics
    dentistry_field, created = ResearchField.objects.get_or_create(
        name='Dentistry',
        defaults={'description': 'Dental research and oral health'}
    )
    
    # Update statistics
    dental_journals_count = Journal.objects.filter(
        broad_subject_terms__icontains='Dentistry'
    ).count()
    
    dentistry_field.total_journals = dental_journals_count
    dentistry_field.save()
    
    print(f"   ✅ Updated Dentistry field with {dental_journals_count:,} journals")

def main():
    """Main function"""
    print(f"🚀 Starting dental journals import to Railway...")
    print(f"⏰ Time: {datetime.now()}")
    
    # Check if we're connected to Railway (PostgreSQL)
    from django.conf import settings
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'postgresql' not in db_engine:
        print("⚠️  Warning: Not connected to PostgreSQL database")
        print("This script is designed for Railway PostgreSQL import")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Import cancelled")
            return
    
    if import_dental_journals():
        update_research_fields()
        print(f"\n🎉 All done! Dental journals successfully added to Railway database")
        print(f"🌐 Your dental journals are now available at: https://ost.xeradb.com/journals/")
    else:
        print(f"\n❌ Import failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 