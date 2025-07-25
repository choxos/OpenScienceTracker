from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from tracker.models import Paper, Journal
import pandas as pd
import os
from django.utils import timezone
from datetime import datetime
from tqdm import tqdm
import psutil
import gc

class Command(BaseCommand):
    help = 'Import rtransparent medicaltransparency_opendata.csv with correct field mapping'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to rtransparent CSV file')
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch (default: 1000)'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=10000,
            help='Number of rows to read into memory at once (default: 10000)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of records to import (for testing)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing papers instead of ignoring conflicts'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        chunk_size = options['chunk_size']
        limit = options['limit']
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'❌ File not found: {csv_file}'))
            return

        self.stdout.write(self.style.SUCCESS(f'🔬 Importing rtransparent medical data from: {csv_file}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 DRY RUN MODE - No data will be imported'))

        # Check existing papers
        existing_count = Paper.objects.count()
        self.stdout.write(f'📊 Existing papers in database: {existing_count:,}')

        # Get file size and estimate
        file_size = os.path.getsize(csv_file) / (1024 * 1024)  # MB
        self.stdout.write(f'📁 File size: {file_size:.1f} MB')

        # Load journals for mapping
        self.stdout.write('🏥 Loading journal mappings...')
        journal_map = self.build_journal_map()

        total_processed = 0
        total_imported = 0
        total_errors = 0

        try:
            # Read CSV in chunks
            chunk_reader = pd.read_csv(csv_file, chunksize=chunk_size, dtype=str, na_filter=False)
            
            for chunk_num, chunk_df in enumerate(chunk_reader, 1):
                if limit and total_processed >= limit:
                    break

                # Limit chunk if needed
                if limit:
                    remaining = limit - total_processed
                    if remaining < len(chunk_df):
                        chunk_df = chunk_df.head(remaining)

                self.stdout.write(f'📦 Processing chunk {chunk_num} ({len(chunk_df):,} rows)')
                
                chunk_imported, chunk_errors = self.process_chunk(
                    chunk_df, journal_map, batch_size, chunk_num, dry_run, update_existing
                )
                
                total_processed += len(chunk_df)
                total_imported += chunk_imported
                total_errors += chunk_errors

                # Memory management
                del chunk_df
                gc.collect()

                # Show progress
                memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                self.stdout.write(
                    f'Progress: {total_processed:,} processed, '
                    f'{total_imported:,} imported, '
                    f'{total_errors:,} errors, '
                    f'{memory_mb:.1f} MB memory'
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {e}'))
            return

        # Final summary
        final_count = Paper.objects.count()
        self.stdout.write(self.style.SUCCESS('✅ rtransparent import completed!'))
        self.stdout.write(f'📊 Total papers in database: {final_count:,}')
        self.stdout.write(f'🔬 rtransparent papers imported: {total_imported:,}')
        self.stdout.write(f'📈 Records processed: {total_processed:,}')
        if total_errors > 0:
            self.stdout.write(f'⚠️ Errors encountered: {total_errors:,}')

    def build_journal_map(self):
        """Build a mapping of journal identifiers to Journal objects"""
        journal_map = {}
        
        # Map by title
        for journal in Journal.objects.all():
            if journal.title_full:
                journal_map[journal.title_full.lower().strip()] = journal.id
            if journal.title_abbreviation:
                journal_map[journal.title_abbreviation.lower().strip()] = journal.id
        
        return journal_map

    def find_journal_id(self, row, journal_map):
        """Find the appropriate journal ID for a paper"""
        journal_title = self.clean_field(row.get('journalTitle', ''))
        journal_issn = self.clean_field(row.get('journalIssn', ''))
        
        # Try exact title match first
        if journal_title:
            journal_key = journal_title.lower().strip()
            if journal_key in journal_map:
                return journal_map[journal_key]
        
        # Try ISSN match
        if journal_issn:
            try:
                journal = Journal.objects.filter(
                    models.Q(issn_electronic=journal_issn) |
                    models.Q(issn_print=journal_issn) |
                    models.Q(issn_linking=journal_issn)
                ).first()
                if journal:
                    return journal.id
            except:
                pass
        
        return None

    def process_chunk(self, chunk_df, journal_map, batch_size, chunk_num, dry_run, update_existing):
        """Process a chunk of rtransparent data"""
        chunk_df = chunk_df.fillna('')
        
        papers = []
        imported_count = 0
        error_count = 0
        
        chunk_progress = tqdm(
            chunk_df.iterrows(), 
            desc=f"Processing rtransparent chunk {chunk_num}", 
            total=len(chunk_df),
            leave=False,
            unit="rows"
        )
        
        for idx, row in chunk_progress:
            try:
                # Create epmc_id from available identifiers
                epmc_id = self.generate_epmc_id(row)
                if not epmc_id:
                    error_count += 1
                    continue
                
                # Skip if exists and not updating
                if not update_existing:
                    if Paper.objects.filter(epmc_id=epmc_id).exists():
                        continue
                
                # Find journal
                journal_id = self.find_journal_id(row, journal_map)
                
                # Extract publication year from date
                pub_year = self.extract_year_from_date(row.get('firstPublicationDate'))
                
                # Create Paper instance with correct field mapping
                paper_data = {
                    'epmc_id': epmc_id,
                    'source': 'rtransparent',  # Mark as rtransparent source
                    'pmid': self.clean_varchar(row.get('pmid'), 20),
                    'pmcid': self.clean_varchar(row.get('pmcid'), 20),
                    'doi': self.clean_field(row.get('doi')),
                    'title': self.clean_field(row.get('title')) or 'Unknown Title',
                    'author_string': self.clean_field(row.get('authorString')),
                    'journal_title': self.clean_field(row.get('journalTitle')) or 'Unknown Journal',
                    'journal_issn': self.clean_field(row.get('journalIssn')),
                    'pub_year': pub_year,  # Remove 2020 fallback - let None be None for missing dates
                    'first_publication_date': self.clean_date(row.get('firstPublicationDate')),
                    'journal_volume': self.clean_varchar(row.get('journalVolume'), 20),
                    'page_info': self.clean_varchar(row.get('pageInfo'), 50),
                    'issue': self.clean_varchar(row.get('issue'), 20),
                    'pub_type': self.clean_varchar(row.get('type'), 200),
                    
                    # rtransparent transparency indicators
                    'is_coi_pred': self.clean_boolean(row.get('is_coi_pred')),
                    'coi_text': self.clean_field(row.get('coi_text')),
                    'is_fund_pred': self.clean_boolean(row.get('is_fund_pred')),
                    'fund_text': self.clean_field(row.get('fund_text')),
                    'is_register_pred': self.clean_boolean(row.get('is_register_pred')),
                    'register_text': self.clean_field(row.get('register_text')),
                    'is_open_data': self.clean_boolean(row.get('is_open_data')),
                    'open_data_category': self.clean_field(row.get('open_data_category')),
                    'open_data_statements': self.clean_field(row.get('open_data_statements')),
                    'is_open_code': self.clean_boolean(row.get('is_open_code')),
                    'open_code_statements': self.clean_field(row.get('open_code_statements')),
                    
                    # Calculate transparency score
                    'transparency_score': self.calculate_transparency_score(row),
                    
                    # Assessment metadata
                    'assessment_tool': 'rtransparent',
                    'transparency_processed': True,
                    
                    # Journal reference
                    'journal_id': journal_id,
                }
                
                if dry_run:
                    # Just count for dry run
                    imported_count += 1
                    if imported_count <= 5:  # Show first 5 for preview
                        self.stdout.write(f"Would import: {epmc_id} - {paper_data['title'][:50]}...")
                else:
                    if update_existing:
                        paper, created = Paper.objects.update_or_create(
                            epmc_id=epmc_id,
                            defaults=paper_data
                        )
                        if created:
                            imported_count += 1
                    else:
                        paper = Paper(**paper_data)
                        papers.append(paper)
                
                # Batch insert for new papers
                if not dry_run and not update_existing and len(papers) >= batch_size:
                    with transaction.atomic():
                        Paper.objects.bulk_create(papers, ignore_conflicts=True)
                    imported_count += len(papers)
                    papers = []
                
            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Show first 10 errors
                    self.stdout.write(f"Error processing row {idx}: {e}")
        
        # Insert remaining papers
        if not dry_run and not update_existing and papers:
            with transaction.atomic():
                Paper.objects.bulk_create(papers, ignore_conflicts=True)
            imported_count += len(papers)
        
        return imported_count, error_count

    def generate_epmc_id(self, row):
        """Generate a unique epmc_id from available identifiers"""
        pmcid = self.clean_field(row.get('pmcid'))
        pmid = self.clean_field(row.get('pmid'))
        doi = self.clean_field(row.get('doi'))
        
        # Prefer PMC ID if available
        if pmcid and pmcid.startswith('PMC'):
            return pmcid
        elif pmcid:
            return f"PMC{pmcid}"
        
        # Fall back to PMID
        if pmid:
            return f"PMID{pmid}"
        
        # Last resort: DOI-based ID
        if doi:
            # Create a short hash from DOI
            import hashlib
            doi_hash = hashlib.md5(doi.encode()).hexdigest()[:8]
            return f"DOI{doi_hash}"
        
        return None

    def extract_year_from_date(self, date_str):
        """Extract year from firstPublicationDate"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y']:
                try:
                    return datetime.strptime(date_str.split()[0], fmt).year
                except:
                    continue
            
            # Try extracting first 4 digits as year
            year_match = ''.join(filter(str.isdigit, date_str))[:4]
            if len(year_match) == 4:
                year = int(year_match)
                if 1900 <= year <= 2030:
                    return year
        except:
            pass
        
        return None

    def calculate_transparency_score(self, row):
        """Calculate transparency score from rtransparent indicators"""
        score = 0
        
        # Count transparency indicators (0-6 scale)
        indicators = [
            'is_coi_pred', 'is_fund_pred', 'is_register_pred',
            'is_open_data', 'is_open_code'
        ]
        
        for indicator in indicators:
            if self.clean_boolean(row.get(indicator)):
                score += 1
        
        return score

    # Utility methods for data cleaning
    def clean_field(self, value):
        """Clean a general field"""
        if pd.isna(value) or value == '' or value == 'nan':
            return None
        return str(value).strip()

    def clean_varchar(self, value, max_length):
        """Clean and truncate varchar field"""
        cleaned = self.clean_field(value)
        if cleaned and len(cleaned) > max_length:
            return cleaned[:max_length]
        return cleaned

    def clean_boolean(self, value):
        """Clean boolean field"""
        if pd.isna(value) or value == '' or value == 'nan':
            return False
        
        value_str = str(value).lower().strip()
        return value_str in ['true', '1', 'yes', 't', 'y']

    def clean_date(self, value):
        """Clean date field"""
        if not self.clean_field(value):
            return None
        
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']:
                try:
                    return datetime.strptime(value.split()[0], fmt).date()
                except:
                    continue
        except:
            pass
        
        return None 