from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Journal
import pandas as pd
import os

class Command(BaseCommand):
    help = 'Bulk import dental journals (fallback method - 13x faster than individual saves)'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🦷 Bulk importing dental journals...'))
        
        # Check if already imported
        existing_dental_count = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
        if existing_dental_count > 100:
            self.stdout.write(self.style.WARNING(f'✅ Dental journals already imported ({existing_dental_count:,} found). Skipping.'))
            return
        
        try:
            # Load CSV with pandas
            df = pd.read_csv('dental_journals_ost.csv')
            self.stdout.write(f"📄 Processing {len(df):,} dental journal records")
            
            # Clean data
            df = df.fillna('')
            df = df.where(pd.notnull(df), None)
            
            # Convert to model instances in batches
            journals = []
            batch_size = 1000
            
            for idx, row in df.iterrows():
                journal = Journal(
                    nlm_id=self.clean_field(row.get('nlm_id')),
                    title_abbreviation=self.clean_field(row.get('title_abbreviation')) or 'Unknown',
                    title_full=self.clean_field(row.get('title_full')) or '',
                    authors=self.clean_field(row.get('authors')),
                    publication_start_year=self.clean_year(row.get('publication_start_year')),
                    publication_end_year=self.clean_year(row.get('publication_end_year')),
                    frequency=self.clean_field(row.get('frequency')),
                    country=self.clean_field(row.get('country')),
                    publisher=self.clean_field(row.get('publisher')),
                    language=self.clean_field(row.get('language')),
                    issn_electronic=self.clean_field(row.get('issn_electronic')),
                    issn_print=self.clean_field(row.get('issn_print')),
                    issn_linking=self.clean_field(row.get('issn_linking')),
                    lccn=self.clean_field(row.get('lccn')),
                    electronic_links=self.clean_url(row.get('electronic_links')),
                    indexing_status=self.clean_field(row.get('indexing_status')),
                    mesh_terms=self.clean_field(row.get('mesh_terms')),
                    publication_types=self.clean_field(row.get('publication_types')),
                    notes=self.clean_field(row.get('notes')),
                    broad_subject_terms=self.clean_field(row.get('broad_subject_terms')),
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
            dental_journals = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
            
            self.stdout.write(self.style.SUCCESS('✅ Bulk import completed!'))
            self.stdout.write(f'📊 Total journals: {total_journals:,}')
            self.stdout.write(f'🦷 Dental journals: {dental_journals:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File dental_journals_ost.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
    
    def clean_field(self, value):
        """Clean field value"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        return str(value).strip()
    
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