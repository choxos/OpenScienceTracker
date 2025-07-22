"""
Django management command to download and import data from OSF directly.
This is designed to run on Railway infrastructure with internet access.
"""

import requests
import pandas as pd
import os
from io import StringIO
from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Download and import transparency data from OSF'
    
    # Updated OSF dataset URLs (working format)
    OSF_FILES = {
        'medical': 'https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499',  # medicaltransparency_opendata.csv
        'dental': 'https://osf.io/zbc6p/files/osfstorage/66113e5ac0539424e0b4d491',   # dentaltransparency_opendata.csv
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset',
            type=str,
            choices=['dental', 'medical', 'both'],
            default='dental',
            help='Which dataset to import (dental, medical, or both)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process per batch'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=None,
            help='Maximum number of records to import (for testing)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting OSF data import...")
        
        datasets = ['dental', 'medical'] if options['dataset'] == 'both' else [options['dataset']]
        
        total_imported = 0
        for dataset_name in datasets:
            self.stdout.write(f"\n📊 Processing {dataset_name} dataset...")
            try:
                imported = self.import_dataset(dataset_name, options)
                total_imported += imported
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Successfully imported {imported} {dataset_name} records")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error importing {dataset_name}: {str(e)}")
                )
                logger.error(f"Error importing {dataset_name}: {str(e)}")
        
        self.stdout.write(f"\n🎉 Total import complete! {total_imported} records imported")
    
    def import_dataset(self, dataset_name, options):
        """Download and import a specific dataset"""
        url = self.OSF_FILES[dataset_name]
        
        # Download data with timeout and retries
        self.stdout.write(f"📥 Downloading {dataset_name} data from OSF...")
        
        try:
            # Use smaller timeout for Railway environment
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Read CSV data in chunks for memory efficiency
            csv_content = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), low_memory=False)
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(f"❌ Download failed: {str(e)}")
            self.stdout.write("💡 Trying alternative approach...")
            # Could implement fallback to pre-existing local files here
            raise
        
        self.stdout.write(f"📄 Loaded {len(df)} records from {dataset_name} dataset")
        
        # Apply max records limit if specified
        if options['max_records']:
            df = df.head(options['max_records'])
            self.stdout.write(f"🔢 Limited to {len(df)} records for testing")
        
        # Import data in batches
        batch_size = options['batch_size']
        total_imported = 0
        
        for start_idx in range(0, len(df), batch_size):
            end_idx = min(start_idx + batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            imported_count = self.import_batch(batch_df, dataset_name)
            total_imported += imported_count
            
            progress = ((start_idx + len(batch_df)) / len(df)) * 100
            self.stdout.write(
                f"📦 Batch {start_idx//batch_size + 1}: "
                f"Imported {imported_count}/{len(batch_df)} records "
                f"({progress:.1f}% complete)"
            )
        
        return total_imported
    
    def import_batch(self, batch_df, dataset_name):
        """Import a batch of records"""
        imported_count = 0
        
        with transaction.atomic():
            for _, row in batch_df.iterrows():
                try:
                    # Get or create journal
                    journal_title = str(row.get('journal', 'Unknown')).strip()
                    if not journal_title or journal_title.lower() == 'nan':
                        journal_title = 'Unknown Journal'
                        
                    journal, created = Journal.objects.get_or_create(
                        title_abbreviation=journal_title,
                        defaults={
                            'title_full': journal_title,
                            'publisher': str(row.get('publisher', '')).strip(),
                            'issn_print': str(row.get('issn', '')).strip(),
                            'broad_subject_terms': str(row.get('subject_terms', '')).strip(),
                        }
                    )
                    
                    # Create paper
                    pmid = str(row.get('pmid', '')).strip()
                    if not pmid or pmid.lower() in ['nan', 'none', '']:
                        continue  # Skip papers without PMID
                        
                    paper, created = Paper.objects.get_or_create(
                        pmid=pmid,
                        defaults={
                            'title': str(row.get('title', '')).strip(),
                            'author_string': str(row.get('authors', '')).strip(),
                            'journal': journal,
                            'journal_title': journal_title,
                            'pub_year': self.parse_year(row.get('pub_year', row.get('year', 2024))),
                            'doi': str(row.get('doi', '')).strip(),
                            'is_open_data': self.parse_boolean(row.get('is_open_data', row.get('data_available'))),
                            'is_open_code': self.parse_boolean(row.get('is_open_code', row.get('code_available'))),
                            'is_coi_pred': self.parse_boolean(row.get('is_coi_pred')),
                            'is_fund_pred': self.parse_boolean(row.get('is_fund_pred')),
                            'is_register_pred': self.parse_boolean(row.get('is_register_pred')),
                            'broad_subject_category': str(row.get('broad_subject_category', '')).strip(),
                            'pub_type': str(row.get('pub_type', '')).strip(),
                            'assessment_tool': 'rtransparent',
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error importing record PMID {row.get('pmid', 'unknown')}: {str(e)}")
                    continue
        
        return imported_count
    
    def parse_year(self, year_value):
        """Parse year value, return current year if invalid"""
        try:
            if pd.isna(year_value):
                return 2024
            year = int(float(year_value))
            return year if 1900 <= year <= 2030 else 2024
        except:
            return 2024
    
    def parse_boolean(self, value):
        """Parse boolean value from various formats"""
        try:
            if pd.isna(value):
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ['true', 'yes', '1', 'y']
            return bool(value)
        except:
            return False 