from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Journal
import pandas as pd

class Command(BaseCommand):
    help = 'Import dental journals from dental_journals_ost.csv'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📚 Importing dental journals...'))
        
        try:
            # Load dental journal database
            df = pd.read_csv('dental_journals_ost.csv')
            self.stdout.write(f"📄 Processing {len(df):,} journal records")
            
            # Clean data
            df = df.fillna('')
            df = df.where(pd.notnull(df), None)
            
            # Convert to model instances in batches
            journals = []
            batch_size = 100
            
            for idx, row in df.iterrows():
                # Create Journal instance
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
                    issn_electronic=self.clean_issn(row.get('issn_electronic')),
                    issn_print=self.clean_issn(row.get('issn_print')),
                    issn_linking=self.clean_issn(row.get('issn_linking')),
                    lccn=self.clean_field(row.get('lccn')),
                    electronic_links=self.clean_field(row.get('electronic_links')),
                    indexing_status=self.clean_field(row.get('indexing_status')),
                    mesh_terms=self.clean_field(row.get('mesh_terms')),
                    publication_types=self.clean_field(row.get('publication_types')),
                    notes=self.clean_field(row.get('notes')),
                    broad_subject_terms=self.clean_field(row.get('broad_subject_terms')) or 'Dentistry',
                    subject_term_count=self.clean_number(row.get('subject_term_count')) or 1,
                )
                journals.append(journal)
                
                # Batch insert every 100 records
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
            
            self.stdout.write(self.style.SUCCESS('✅ Dental journals import completed!'))
            self.stdout.write(f'📊 Total journals: {total_journals:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File dental_journals_ost.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}'))
    
    def clean_field(self, value):
        """Clean field value"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        return str(value).strip()
    
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
    
    def clean_issn(self, value):
        """Clean ISSN field"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        issn = str(value).strip()
        # Basic ISSN validation (8 digits with optional dash)
        if len(issn) in [8, 9] and issn.replace('-', '').isdigit():
            return issn
        return "" 