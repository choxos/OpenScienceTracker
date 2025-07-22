"""
Django management command to download and import data from OSF directly.
This is designed to run on Railway infrastructure with internet access.
"""

import requests
import zipfile
import pandas as pd
import os
import tempfile
from io import StringIO
from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal, PaperType
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Download and import transparency data from OSF'
    
    # OSF dataset URLs
    OSF_FILES = {
        'dental': 'https://osf.io/download/sj9cn/',  # dental_transparency_opendata.csv
        'medical': 'https://osf.io/download/ek8ra/'   # medical_transparency_opendata.csv
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset',
            type=str,
            choices=['dental', 'medical', 'both'],
            default='both',
            help='Which dataset to import (dental, medical, or both)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
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
        
        for dataset_name in datasets:
            self.stdout.write(f"\n📊 Processing {dataset_name} dataset...")
            try:
                self.import_dataset(dataset_name, options)
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Successfully imported {dataset_name} dataset")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error importing {dataset_name}: {str(e)}")
                )
                logger.error(f"Error importing {dataset_name}: {str(e)}")
    
    def import_dataset(self, dataset_name, options):
        """Download and import a specific dataset"""
        url = self.OSF_FILES[dataset_name]
        
        # Download data
        self.stdout.write(f"📥 Downloading {dataset_name} data from OSF...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Read CSV data
        csv_content = response.content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
        
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
            
            self.stdout.write(
                f"📦 Batch {start_idx//batch_size + 1}: "
                f"Imported {imported_count}/{len(batch_df)} records "
                f"(Total: {total_imported})"
            )
        
        self.stdout.write(f"🎉 Import complete! Total imported: {total_imported}")
    
    def import_batch(self, batch_df, dataset_name):
        """Import a batch of records"""
        imported_count = 0
        
        with transaction.atomic():
            for _, row in batch_df.iterrows():
                try:
                    # Get or create journal
                    journal, created = Journal.objects.get_or_create(
                        name=row.get('journal', 'Unknown'),
                        defaults={
                            'publisher': row.get('publisher', ''),
                            'issn': row.get('issn', ''),
                        }
                    )
                    
                    # Get or create paper type
                    paper_type_name = row.get('study_type', 'Unknown')
                    paper_type, created = PaperType.objects.get_or_create(
                        name=paper_type_name
                    )
                    
                    # Create paper
                    paper, created = Paper.objects.get_or_create(
                        pmid=str(row.get('pmid', '')),
                        defaults={
                            'title': row.get('title', ''),
                            'authors': row.get('authors', ''),
                            'journal': journal,
                            'publication_date': self.parse_date(row.get('publication_date')),
                            'doi': row.get('doi', ''),
                            'has_data_availability_statement': self.parse_boolean(row.get('has_data_statement')),
                            'data_available': self.parse_boolean(row.get('data_available')),
                            'data_location': row.get('data_location', ''),
                            'has_analysis_code': self.parse_boolean(row.get('has_code')),
                            'code_location': row.get('code_location', ''),
                            'paper_type': paper_type,
                            'dataset_source': dataset_name,
                            'subject_terms': row.get('subject_terms', ''),
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error importing record PMID {row.get('pmid', 'unknown')}: {str(e)}")
                    continue
        
        return imported_count
    
    def parse_date(self, date_str):
        """Parse date string, return None if invalid"""
        if pd.isna(date_str):
            return None
        try:
            return pd.to_datetime(date_str).date()
        except:
            return None
    
    def parse_boolean(self, value):
        """Parse boolean value from various formats"""
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '1', 'y']
        return bool(value) 