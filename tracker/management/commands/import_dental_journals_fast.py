from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Journal
import pandas as pd
import os
from io import StringIO

class Command(BaseCommand):
    help = 'Ultra-fast import dental journals using PostgreSQL COPY (up to 77x faster)'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🚀 Fast importing dental journals with PostgreSQL COPY...'))
        
        # Check if already imported to avoid duplicates
        existing_dental_count = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
        if existing_dental_count > 100:
            self.stdout.write(self.style.WARNING(f'✅ Dental journals already imported ({existing_dental_count:,} found). Skipping.'))
            return
        
        try:
            # Load CSV with pandas
            df = pd.read_csv('dental_journals_ost.csv')
            self.stdout.write(f"📄 Loaded {len(df):,} dental journal records from CSV")
            
            # Clean and prepare data for PostgreSQL COPY
            df = df.fillna('')  # Replace NaN with empty strings
            
            # Handle numeric fields properly
            for col in ['publication_start_year', 'publication_end_year', 'subject_term_count']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # Clean string fields
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).fillna('')
            
            # Reorder columns to match model field order for COPY
            column_order = [
                'nlm_id', 'title_abbreviation', 'title_full', 'authors',
                'publication_start_year', 'publication_end_year', 'frequency',
                'country', 'publisher', 'language', 'issn_electronic', 
                'issn_print', 'issn_linking', 'lccn', 'electronic_links',
                'indexing_status', 'mesh_terms', 'publication_types', 
                'notes', 'broad_subject_terms', 'subject_term_count'
            ]
            
            # Ensure all columns exist
            for col in column_order:
                if col not in df.columns:
                    df[col] = ''
            
            # Select and reorder columns
            df_ordered = df[column_order]
            
            # Create in-memory CSV buffer for COPY command
            csv_buffer = StringIO()
            df_ordered.to_csv(csv_buffer, index=False, header=False, sep='\t', na_rep='')
            csv_buffer.seek(0)
            
            # Use PostgreSQL COPY for ultra-fast bulk insert
            with transaction.atomic():
                # Map CSV columns to model fields
                mapping = dict(zip(range(len(column_order)), column_order))
                
                Journal.objects.from_csv(
                    csv_buffer,
                    mapping=mapping,
                    delimiter='\t'
                )
            
            # Report results
            total_journals = Journal.objects.count()
            dental_journals = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
            
            self.stdout.write(self.style.SUCCESS('✅ Ultra-fast import completed!'))
            self.stdout.write(f'📊 Total journals in database: {total_journals:,}')
            self.stdout.write(f'🦷 Dental journals imported: {dental_journals:,}')
            self.stdout.write(f'⚡ Import method: PostgreSQL COPY (up to 77x faster than regular Django)')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File dental_journals_ost.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}')) 