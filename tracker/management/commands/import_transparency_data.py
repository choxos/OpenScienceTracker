import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tracker.models import Paper
from datetime import datetime

class Command(BaseCommand):
    help = 'Import transparency data from rtransparent CSV files (transparency_[year]_[month].csv)'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the transparency CSV file (e.g., transparency_1900_01.csv)'
        )
        parser.add_argument(
            '--folder',
            type=str,
            help='Path to folder containing multiple transparency CSV files'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process per batch (default: 500)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--open-access-only',
            action='store_true',
            help='Only process papers marked as open access',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.open_access_only = options['open_access_only']
        self.batch_size = options['batch_size']
        
        if options['folder']:
            self.import_folder(options['folder'])
        else:
            self.import_file(options['csv_file'])

    def import_folder(self, folder_path):
        """Import all transparency CSV files from a folder"""
        if not os.path.exists(folder_path):
            raise CommandError(f'Folder does not exist: {folder_path}')
        
        # Find all files matching pattern transparency_*.csv
        csv_files = []
        for filename in os.listdir(folder_path):
            if filename.startswith('transparency_') and filename.endswith('.csv'):
                csv_files.append(os.path.join(folder_path, filename))
        
        if not csv_files:
            raise CommandError(f'No transparency_*.csv files found in folder: {folder_path}')
        
        csv_files.sort()  # Process in chronological order
        self.stdout.write(f"📁 Found {len(csv_files)} transparency CSV files to import")
        
        total_updated = 0
        total_matched = 0
        
        for csv_file in csv_files:
            self.stdout.write(f"\n📄 Processing: {os.path.basename(csv_file)}")
            updated, matched = self.import_file(csv_file)
            total_updated += updated
            total_matched += matched
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Folder import complete!\n"
                f"   🔄 Total updated: {total_updated:,} papers\n"
                f"   🎯 Total matched: {total_matched:,} papers\n"
                f"   📁 Files processed: {len(csv_files)}"
            )
        )

    def import_file(self, csv_file):
        """Import a single transparency CSV file"""
        if not os.path.exists(csv_file):
            raise CommandError(f'File does not exist: {csv_file}')

        self.stdout.write(f"🔬 Loading transparency data from: {csv_file}")
        
        try:
            # Load CSV with pandas
            df = pd.read_csv(csv_file)
            total_rows = len(df)
            self.stdout.write(f"📄 Found {total_rows:,} records in CSV")
            
            # Validate required columns
            required_cols = ['pmid']  # PMID is our primary key for matching
            transparency_cols = [
                'rt_all_is_coi_pred', 'rt_all_coi_text',
                'rt_all_is_fund_pred', 'rt_all_fund_text', 
                'rt_all_is_register_pred', 'rt_all_register_text',
                'rt_data_is_open_data', 'rt_data_open_data_category', 'rt_data_open_data_statements',
                'rt_data_is_open_code', 'rt_data_open_code_statements'
            ]
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise CommandError(f'Missing required columns: {missing_cols}')
            
            # Filter to only records with transparency data
            df_filtered = self.filter_transparency_data(df, transparency_cols)
            
            if self.dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"🔍 DRY RUN: Would process {len(df_filtered):,} records with transparency data\n"
                        f"   Total CSV records: {total_rows:,}\n"
                        f"   With transparency data: {len(df_filtered):,}\n"
                        f"   Sample transparency indicators:\n{self.get_sample_transparency(df_filtered)}"
                    )
                )
                return 0, len(df_filtered)
            
            # Import data in batches
            updated_count, matched_count = self.process_dataframe(df_filtered)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Transparency import complete!\n"
                    f"   🔄 Updated: {updated_count:,} papers\n"
                    f"   🎯 Matched: {matched_count:,} papers with transparency data\n"
                    f"   📁 File: {os.path.basename(csv_file)}"
                )
            )
            
            return updated_count, matched_count
            
        except Exception as e:
            raise CommandError(f'Error processing transparency CSV file: {str(e)}')

    def filter_transparency_data(self, df, transparency_cols):
        """Filter to only records that have transparency data"""
        # Keep records that have at least one transparency indicator
        has_transparency = df[transparency_cols].notna().any(axis=1)
        
        # Also filter by PMID (must have PMID for matching)
        has_pmid = df['pmid'].notna() & (df['pmid'] != '') & (df['pmid'] != 'nan')
        
        filtered_df = df[has_transparency & has_pmid].copy()
        
        self.stdout.write(f"📊 Filtered to {len(filtered_df):,} records with transparency data and valid PMID")
        
        return filtered_df

    def get_sample_transparency(self, df):
        """Get a sample of transparency indicators for dry run"""
        if len(df) == 0:
            return "No records with transparency data"
        
        sample = df.head(3)
        result = []
        for _, row in sample.iterrows():
            indicators = []
            if self.safe_bool(row.get('rt_all_is_coi_pred')):
                indicators.append('COI')
            if self.safe_bool(row.get('rt_all_is_fund_pred')):
                indicators.append('Fund')
            if self.safe_bool(row.get('rt_all_is_register_pred')):
                indicators.append('Reg')
            if self.safe_bool(row.get('rt_data_is_open_data')):
                indicators.append('Data')
            if self.safe_bool(row.get('rt_data_is_open_code')):
                indicators.append('Code')
            
            result.append(f"PMID {row.get('pmid')}: {', '.join(indicators) if indicators else 'None'}")
        
        return '\n'.join(result)

    def process_dataframe(self, df):
        """Process dataframe in batches"""
        updated_count = 0
        matched_count = len(df)
        
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            self.stdout.write(f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_df)} records)")
            
            with transaction.atomic():
                for _, row in batch_df.iterrows():
                    try:
                        updated = self.update_paper_transparency(row)
                        if updated:
                            updated_count += 1
                            
                        # Progress indicator
                        if updated_count % 50 == 0 and updated_count > 0:
                            self.stdout.write(f"   🔄 Updated: {updated_count:,} papers", ending='\r')
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error processing PMID {row.get('pmid', 'unknown')}: {str(e)}")
                        )
                        continue
        
        return updated_count, matched_count

    def update_paper_transparency(self, row):
        """Update transparency data for a paper"""
        pmid = str(row['pmid']).strip()
        
        # Find paper by PMID
        try:
            paper = Paper.objects.get(pmid=pmid)
        except Paper.DoesNotExist:
            # Try alternative identifier matching
            # Try PMCID if available
            pmcid = str(row.get('pmcid', '')).strip()
            if pmcid:
                try:
                    paper = Paper.objects.get(pmcid=pmcid)
                except Paper.DoesNotExist:
                    # Paper not found
                    return False
            else:
                return False
        except Paper.MultipleObjectsReturned:
            self.stdout.write(self.style.WARNING(f"⚠️ Multiple papers found for PMID {pmid}, using first"))
            paper = Paper.objects.filter(pmid=pmid).first()
        
        # Check if we should only process open access papers
        if self.open_access_only and not paper.is_open_access:
            return False
        
        # Update transparency indicators
        updated = False
        
        # Conflict of Interest
        if 'rt_all_is_coi_pred' in row:
            new_value = self.safe_bool(row['rt_all_is_coi_pred'])
            if paper.is_coi_pred != new_value:
                paper.is_coi_pred = new_value
                updated = True
        
        if 'rt_all_coi_text' in row:
            new_text = self.safe_text(row['rt_all_coi_text'])
            if paper.coi_text != new_text:
                paper.coi_text = new_text
                updated = True
        
        # Funding
        if 'rt_all_is_fund_pred' in row:
            new_value = self.safe_bool(row['rt_all_is_fund_pred'])
            if paper.is_fund_pred != new_value:
                paper.is_fund_pred = new_value
                updated = True
        
        if 'rt_all_fund_text' in row:
            new_text = self.safe_text(row['rt_all_fund_text'])
            if paper.fund_text != new_text:
                paper.fund_text = new_text
                updated = True
        
        # Registration
        if 'rt_all_is_register_pred' in row:
            new_value = self.safe_bool(row['rt_all_is_register_pred'])
            if paper.is_register_pred != new_value:
                paper.is_register_pred = new_value
                updated = True
        
        if 'rt_all_register_text' in row:
            new_text = self.safe_text(row['rt_all_register_text'])
            if paper.register_text != new_text:
                paper.register_text = new_text
                updated = True
        
        # Open Data
        if 'rt_data_is_open_data' in row:
            new_value = self.safe_bool(row['rt_data_is_open_data'])
            if paper.is_open_data != new_value:
                paper.is_open_data = new_value
                updated = True
        
        if 'rt_data_open_data_category' in row:
            new_category = self.safe_text(row['rt_data_open_data_category'], max_length=200)
            if paper.open_data_category != new_category:
                paper.open_data_category = new_category
                updated = True
        
        if 'rt_data_open_data_statements' in row:
            new_statements = self.safe_text(row['rt_data_open_data_statements'])
            if paper.open_data_statements != new_statements:
                paper.open_data_statements = new_statements
                updated = True
        
        # Open Code
        if 'rt_data_is_open_code' in row:
            new_value = self.safe_bool(row['rt_data_is_open_code'])
            if paper.is_open_code != new_value:
                paper.is_open_code = new_value
                updated = True
        
        if 'rt_data_open_code_statements' in row:
            new_statements = self.safe_text(row['rt_data_open_code_statements'])
            if paper.open_code_statements != new_statements:
                paper.open_code_statements = new_statements
                updated = True
        
        # Mark as processed and save if updated
        if updated or not paper.transparency_processed:
            paper.transparency_processed = True
            paper.processing_date = timezone.now()
            paper.save()  # This will trigger transparency score calculation
            return True
        
        return False

    def safe_bool(self, value):
        """Safely convert value to boolean"""
        if pd.isna(value) or value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.strip().upper()
            return value in ['TRUE', 'T', '1', 'YES', 'Y']
        try:
            return bool(int(value))
        except:
            return False

    def safe_text(self, value, max_length=None):
        """Safely convert value to text"""
        if pd.isna(value) or value is None:
            return None
        
        text = str(value).strip()
        if text in ['', 'nan', 'None']:
            return None
        
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text 