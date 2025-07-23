from django.core.management.base import BaseCommand
from tracker.models import Paper, Journal
import pandas as pd
import os
from io import StringIO
from django.utils import timezone
from datetime import datetime
import numpy as np

class Command(BaseCommand):
    help = 'Ultra-fast import dental transparency papers using PostgreSQL COPY'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🦷 Fast importing dental transparency papers...'))
        
        # Check if already imported to avoid duplicates
        existing_papers = Paper.objects.filter(journal_title__icontains='dental').count()
        if existing_papers > 1000:
            self.stdout.write(self.style.WARNING(f'✅ Dental papers already imported ({existing_papers:,} found). Skipping.'))
            return
        
        try:
            # Load dental transparency database
            df = pd.read_csv('dental_ost_database.csv')
            self.stdout.write(f"📄 Loaded {len(df):,} dental transparency records from CSV")
            
            # Clean and prepare data
            df = df.fillna('')
            
            # Handle numeric fields properly
            numeric_fields = ['jif2020', 'citedByCount', 'year_firstpub', 'month_firstpub', 'transparency_score', 'transparency_score_pct']
            for col in numeric_fields:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    # Add missing numeric fields with 0 default
                    df[col] = 0
            
            # Handle date fields
            if 'firstPublicationDate' in df.columns:
                df['first_publication_date'] = pd.to_datetime(df['firstPublicationDate'], errors='coerce')
            
            # Handle boolean fields - map to proper True/False, default False for NULL
            boolean_fields = [
                'is_research', 'is_review', 'is_coi_pred', 'is_fund_pred', 'is_register_pred',
                'is_open_data', 'is_open_code', 'is_replication', 'is_novelty'
            ]
            for col in boolean_fields:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.upper().isin(['TRUE', '1', 'YES'])
            
            # Handle disc_* boolean fields (Django model has default=False)
            disc_fields = ['disc_data', 'disc_code', 'disc_coi', 'disc_fund', 'disc_register', 'disc_replication', 'disc_novelty']
            for col in disc_fields:
                if col in df.columns:
                    # Convert to boolean, defaulting False for NULL/empty
                    df[col] = df[col].astype(str).str.upper().isin(['TRUE', '1', 'YES'])
                else:
                    # Add missing disc fields with False default
                    df[col] = False
            
            # Clean string fields
            string_fields = ['pmid', 'pmcid', 'doi', 'title', 'authorString', 'journalTitle', 'journalIssn']
            for col in string_fields:
                if col in df.columns:
                    df[col] = df[col].astype(str).fillna('')
            
            # Handle assessment metadata fields with defaults
            df['assessment_tool'] = df.get('assessment_tool', 'rtransparent').fillna('rtransparent')
            df['ost_version'] = df.get('ost_version', '1.0').fillna('1.0')
            if 'assessment_date' in df.columns:
                df['assessment_date'] = pd.to_datetime(df['assessment_date'], errors='coerce')
            else:
                df['assessment_date'] = timezone.now()
            
            # Add timestamp fields for Django auto fields
            current_time = timezone.now()
            df['created_at'] = current_time
            df['updated_at'] = current_time
            
            # Map to Paper model fields
            column_mapping = {
                'pmid': 'pmid',
                'pmcid': 'pmcid', 
                'doi': 'doi',
                'title': 'title',
                'authorString': 'author_string',
                'journalTitle': 'journal_title',
                'journalIssn': 'journal_issn',
                'jif2020': 'jif2020',
                'publisher': 'scimago_publisher',
                'firstPublicationDate': 'first_publication_date',
                'year_firstpub': 'year_first_pub',
                'month_firstpub': 'month_first_pub',
                'journalVolume': 'journal_volume',
                'pageInfo': 'page_info',
                'issue': 'issue',
                'type': 'pub_type',
                'is_coi_pred': 'is_coi_pred',
                'is_fund_pred': 'is_fund_pred', 
                'is_register_pred': 'is_register_pred',
                'is_open_data': 'is_open_data',
                'is_open_code': 'is_open_code',
                'is_replication': 'is_replication',
                'is_novelty': 'is_novelty',
                'transparency_score': 'transparency_score',
                'transparency_score_pct': 'transparency_score_pct',
                'disc_data': 'disc_data',
                'disc_code': 'disc_code', 
                'disc_coi': 'disc_coi',
                'disc_fund': 'disc_fund',
                'disc_register': 'disc_register',
                'disc_replication': 'disc_replication',
                'disc_novelty': 'disc_novelty',
                'assessment_tool': 'assessment_tool',
                'ost_version': 'ost_version',
                'assessment_date': 'assessment_date',
                'created_at': 'created_at',
                'updated_at': 'updated_at'
            }
            
            # Select and rename columns
            available_cols = [col for col in column_mapping.keys() if col in df.columns]
            df_mapped = df[available_cols].rename(columns=column_mapping)
            
            # Add required fields with defaults
            if 'pub_year' not in df_mapped.columns:
                df_mapped['pub_year'] = df_mapped.get('year_first_pub', 2020)
            if 'journal_id' not in df_mapped.columns:
                df_mapped['journal_id'] = 1  # Default journal ID
            
            # Create in-memory CSV buffer
            csv_buffer = StringIO()
            df_mapped.to_csv(csv_buffer, index=False, header=True, sep='\t', na_rep='')
            csv_buffer.seek(0)
            
            # Use PostgreSQL COPY for ultra-fast bulk insert
            column_mapping_final = {col: col for col in df_mapped.columns}
            
            Paper.objects.from_csv(
                csv_buffer,
                mapping=column_mapping_final,
                delimiter='\t',
                drop_constraints=False,
                drop_indexes=False
            )
            
            # Report results
            total_papers = Paper.objects.count()
            dental_papers = Paper.objects.filter(journal_title__icontains='dental').count()
            
            self.stdout.write(self.style.SUCCESS('✅ Ultra-fast dental papers import completed!'))
            self.stdout.write(f'📊 Total papers in database: {total_papers:,}')
            self.stdout.write(f'🦷 Dental papers imported: {dental_papers:,}')
            self.stdout.write(f'⚡ Import method: PostgreSQL COPY (up to 77x faster)')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File dental_ost_database.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}')) 