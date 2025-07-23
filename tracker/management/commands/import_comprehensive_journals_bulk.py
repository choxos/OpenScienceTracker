from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Journal
import pandas as pd
import os

class Command(BaseCommand):
    help = 'Bulk import comprehensive journals (respects Django defaults)'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('📚 Bulk importing comprehensive journals...'))
        
        # Check if already imported
        existing_journals = Journal.objects.count()
        if existing_journals > 5000:
            self.stdout.write(self.style.WARNING(f'✅ Journals already imported ({existing_journals:,} found). Skipping.'))
            return
        
        try:
            # Load comprehensive journal database
            df = pd.read_csv('comprehensive_journal_database.csv')
            self.stdout.write(f"📄 Processing {len(df):,} journal records")
            
            # Clean data
            df = df.fillna('')
            df = df.where(pd.notnull(df), None)
            
            # Filter out completely empty rows
            key_fields = ['title_abbreviation', 'title_full', 'broad_subject_terms']
            mask_valid = False
            for field in key_fields:
                if field in df.columns:
                    field_mask = (df[field].notna()) & (df[field] != '') & (df[field] != 'nan') & (df[field] != 'None')
                    mask_valid = mask_valid | field_mask if mask_valid is not False else field_mask
            
            if mask_valid is not False:
                original_len = len(df)
                df = df[mask_valid].copy()
                self.stdout.write(f"🔍 Filtered {original_len - len(df)} empty journal records")
            
            # Convert to model instances in batches
            journals = []
            batch_size = 1000
            
            for idx, row in df.iterrows():
                # Create Journal instance - Django will apply model defaults
                journal = Journal(
                    nlm_id=self.clean_field(row.get('nlm_id')),
                    title_abbreviation=self.clean_title_abbrev(row),
                    title_full=self.clean_field(row.get('title_full')) or '',
                    authors=self.clean_field(row.get('authors')),
                    publication_start_year=self.clean_year(row.get('publication_start_year')),
                    publication_end_year=self.clean_year(row.get('publication_end_year')),
                    frequency=self.clean_field(row.get('frequency')),
                    country=self.clean_field(row.get('country')),
                    publisher=self.clean_field(row.get('publisher')),
                    language=self.clean_field(row.get('language')),
                    issn_electronic=self.clean_issn(row.get('issn_electronic')),
                    issn_print=self.clean_issn(row.get('issn_print')),
                    issn_linking=self.clean_issn(row.get('issn_linking')),
                    lccn=self.clean_field(row.get('lccn')),
                    electronic_links=self.clean_url(row.get('electronic_links')),
                    indexing_status=self.clean_field(row.get('indexing_status')),
                    mesh_terms=self.clean_field(row.get('mesh_terms')),
                    publication_types=self.clean_field(row.get('publication_types')),
                    notes=self.clean_field(row.get('notes')),
                    broad_subject_terms=self.clean_field(row.get('broad_subject_terms')) or 'General',
                    subject_term_count=self.clean_number(row.get('subject_term_count')) or 1,
                )
                journals.append(journal)
                
                # Batch insert every 1000 records
                if len(journals) >= batch_size:
                    with transaction.atomic():
                        Journal.objects.bulk_create(journals, ignore_conflicts=True)
                    self.stdout.write(f'  ✅ Imported batch of {len(journals)} journals...')
                    journals = []
            
            # Insert remaining journals
            if journals:
                with transaction.atomic():
                    Journal.objects.bulk_create(journals, ignore_conflicts=True)
                self.stdout.write(f'  ✅ Imported final batch of {len(journals)} journals')
            
            # Report results
            total_journals = Journal.objects.count()
            
            self.stdout.write(self.style.SUCCESS('✅ Bulk journals import completed!'))
            self.stdout.write(f'📊 Total journals imported: {total_journals:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File comprehensive_journal_database.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}'))
    
    def clean_title_abbrev(self, row):
        """Clean title_abbreviation with fallback logic"""
        title_abbrev = self.clean_field(row.get('title_abbreviation'))
        if not title_abbrev or title_abbrev == 'nan':
            # Fallback to truncated title_full
            title_full = self.clean_field(row.get('title_full'))
            if title_full and title_full != 'nan':
                return title_full[:50]
            else:
                return 'Unknown Journal'
        return title_abbrev[:200]  # Ensure max length
    
    def clean_field(self, value):
        """Clean field value"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        return str(value).strip()
    
    def clean_issn(self, value):
        """Clean ISSN field (max 9 chars)"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        issn = str(value).strip()
        return issn[:9] if len(issn) > 9 else issn
    
    def clean_url(self, value):
        """Clean URL field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        url = str(value).strip()
        if not url.startswith(('http://', 'https://')):
            return None
        return url
    
    def clean_year(self, value):
        """Clean year field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            year = int(float(value))
            if 1800 <= year <= 2030:
                return year
        except (ValueError, TypeError):
            pass
        return None
    
    def clean_number(self, value):
        """Clean number field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None 