from django.core.management.base import BaseCommand
from tracker.models import Journal
import pandas as pd
import os
from io import StringIO
from django.utils import timezone

class Command(BaseCommand):
    help = 'Import comprehensive journals database (all fields)'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('📚 Importing comprehensive journals database...'))
        
        # Check if already imported
        existing_journals = Journal.objects.count()
        if existing_journals > 5000:
            self.stdout.write(self.style.WARNING(f'✅ Journals already imported ({existing_journals:,} found). Skipping.'))
            return
        
        try:
            # Load comprehensive journal database
            df = pd.read_csv('comprehensive_journal_database.csv')
            self.stdout.write(f"📄 Loaded {len(df):,} journal records from comprehensive database")
            
            # Clean and prepare data (same logic as dental journals import)
            df = df.fillna('')
            
            # Handle numeric fields
            for col in ['publication_start_year', 'publication_end_year', 'subject_term_count']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # Clean string fields and handle required fields
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).fillna('')
            
            # Handle required title_abbreviation field - use title_full if empty
            if 'title_abbreviation' in df.columns:
                df['title_abbreviation'] = df['title_abbreviation'].fillna('')
                # If title_abbreviation is empty, use truncated title_full
                mask = (df['title_abbreviation'] == '') | (df['title_abbreviation'] == 'nan')
                if 'title_full' in df.columns:
                    df.loc[mask, 'title_abbreviation'] = df.loc[mask, 'title_full'].str[:50]
                else:
                    df.loc[mask, 'title_abbreviation'] = 'Unknown Journal'
            
            # Filter out completely empty rows (all key fields are null/empty)
            key_fields = ['title_abbreviation', 'title_full', 'broad_subject_terms']
            mask_valid = False
            for field in key_fields:
                if field in df.columns:
                    mask_valid |= (df[field].notna()) & (df[field] != '') & (df[field] != 'nan') & (df[field] != 'None')
            
            # If no valid mask created, create one that excludes completely empty rows
            if mask_valid is False:
                mask_valid = ~(df.isnull().all(axis=1))
            
            original_len = len(df)
            df = df[mask_valid].copy()  # Use copy() to avoid warnings
            filtered_len = len(df)
            self.stdout.write(f"🔍 Filtered {original_len - filtered_len} empty journal records")
            
            # Additional cleaning for title_abbreviation after filtering
            if 'title_abbreviation' in df.columns:
                # Replace any remaining NaN/empty with truncated title_full
                mask_bad_title = (df['title_abbreviation'].isnull()) | (df['title_abbreviation'] == '') | (df['title_abbreviation'] == 'nan')
                if mask_bad_title.sum() > 0:
                    self.stdout.write(f"🔧 Fixing {mask_bad_title.sum()} bad title_abbreviation values")
                    if 'title_full' in df.columns:
                        df.loc[mask_bad_title, 'title_abbreviation'] = df.loc[mask_bad_title, 'title_full'].str[:50].fillna('Unknown Journal')
                    else:
                        df.loc[mask_bad_title, 'title_abbreviation'] = 'Unknown Journal'
            
            # Add timestamp fields
            current_time = timezone.now()
            df['created_at'] = current_time
            df['updated_at'] = current_time
            
            # Use existing column order from Journal model
            column_order = [
                'nlm_id', 'title_abbreviation', 'title_full', 'authors',
                'publication_start_year', 'publication_end_year', 'frequency',
                'country', 'publisher', 'language', 'issn_electronic', 
                'issn_print', 'issn_linking', 'lccn', 'electronic_links',
                'indexing_status', 'mesh_terms', 'publication_types', 
                'notes', 'broad_subject_terms', 'subject_term_count',
                'created_at', 'updated_at'
            ]
            
            # Ensure all columns exist
            for col in column_order:
                if col not in df.columns:
                    df[col] = ''
            
            # Select and reorder columns
            df_ordered = df[column_order]
            
            # Create in-memory CSV buffer
            csv_buffer = StringIO()
            df_ordered.to_csv(csv_buffer, index=False, header=True, sep='\t', na_rep='')
            csv_buffer.seek(0)
            
            # Use PostgreSQL COPY
            mapping = {col: col for col in column_order}
            
            Journal.objects.from_csv(
                csv_buffer,
                mapping=mapping,
                delimiter='\t',
                drop_constraints=False,
                drop_indexes=False
            )
            
            # Report results
            total_journals = Journal.objects.count()
            
            self.stdout.write(self.style.SUCCESS('✅ Comprehensive journals import completed!'))
            self.stdout.write(f'📊 Total journals imported: {total_journals:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File comprehensive_journal_database.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}')) 