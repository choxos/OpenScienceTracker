"""
Import rtransparent medical transparency data from CSV
Handles large files (2.5GB+) with chunked processing and bulk operations
"""

import os
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils import timezone
from django.utils.dateparse import parse_date
from tracker.models import Paper, Journal
from datetime import datetime
import logging
from tqdm import tqdm
import gc
import psutil
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import rtransparent medical transparency data from large CSV files efficiently'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the rtransparent CSV file (e.g., medicaltransparency_opendata.csv)'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=1000,
            help='Number of records to process per chunk (default: 1000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to save per batch (default: 500)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of records to process (for testing)'
        )
        parser.add_argument(
            '--skip-rows',
            type=int,
            default=0,
            help='Number of rows to skip (useful for resuming)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing papers instead of skipping them',
        )
        parser.add_argument(
            '--create-journals',
            action='store_true',
            help='Create journal records if they don\'t exist',
        )
        parser.add_argument(
            '--memory-limit',
            type=int,
            default=80,
            help='Memory usage limit percentage (default: 80%)',
        )

    def handle(self, *args, **options):
        self.csv_file = options['csv_file']
        self.chunk_size = options['chunk_size']
        self.batch_size = options['batch_size']
        self.limit = options['limit']
        self.skip_rows = options['skip_rows']
        self.dry_run = options['dry_run']
        self.update_existing = options['update_existing']
        self.create_journals = options['create_journals']
        self.memory_limit = options['memory_limit']
        
        # Validate file exists
        if not os.path.exists(self.csv_file):
            raise CommandError(f'CSV file does not exist: {self.csv_file}')
        
        # Get file info
        file_size = os.path.getsize(self.csv_file) / (1024 * 1024 * 1024)  # GB
        self.stdout.write(self.style.SUCCESS(f'📊 Processing file: {self.csv_file}'))
        self.stdout.write(self.style.SUCCESS(f'📁 File size: {file_size:.2f} GB'))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Start import process
        start_time = time.time()
        self.import_rtransparent_data()
        end_time = time.time()
        
        self.stdout.write(self.style.SUCCESS(f'✅ Import completed in {end_time - start_time:.2f} seconds'))

    def import_rtransparent_data(self):
        """Import rtransparent data with chunked processing"""
        
        # Pre-load journal mapping for better performance
        self.stdout.write('🔍 Loading journal mappings...')
        self.journal_map = self.create_journal_mapping()
        
        # Get total rows for progress tracking
        total_rows = self.get_total_rows()
        if self.limit:
            total_rows = min(total_rows, self.limit)
        
        self.stdout.write(f'📈 Total records to process: {total_rows:,}')
        
        # Process file in chunks
        processed_count = 0
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Create progress bar
        progress_bar = tqdm(total=total_rows, desc="Processing papers", unit="papers")
        
        try:
            # Read CSV in chunks
            chunk_reader = pd.read_csv(
                self.csv_file,
                chunksize=self.chunk_size,
                skiprows=range(1, self.skip_rows + 1) if self.skip_rows > 0 else None,
                dtype={
                    'pmid': 'str',
                    'pmcid': 'str', 
                    'doi': 'str',
                    'journalIssn': 'str',
                    'journalVolume': 'str',
                    'issue': 'str',
                    'pageInfo': 'str',
                    'citedByCount': 'Int64',
                    'is_coi_pred': 'boolean',
                    'is_fund_pred': 'boolean',
                    'is_register_pred': 'boolean',
                    'is_open_data': 'boolean',
                    'is_open_code': 'boolean',
                    'is_research': 'boolean',
                    'is_review': 'boolean',
                    'is_trial': 'boolean'
                },
                na_values=['', 'NULL', 'None', 'NaN', 'null'],
                keep_default_na=True
            )
            
            for chunk_num, chunk_df in enumerate(chunk_reader):
                # Check memory usage
                if self.check_memory_usage():
                    self.stdout.write(self.style.WARNING('⚠️ High memory usage, running garbage collection'))
                    gc.collect()
                
                # Process chunk
                chunk_results = self.process_chunk(chunk_df, chunk_num, progress_bar)
                
                created_count += chunk_results['created']
                updated_count += chunk_results['updated']
                skipped_count += chunk_results['skipped']
                error_count += chunk_results['errors']
                processed_count += len(chunk_df)
                
                # Update progress
                progress_bar.set_description(
                    f"Processed {processed_count:,} | Created {created_count:,} | "
                    f"Updated {updated_count:,} | Errors {error_count:,}"
                )
                
                # Check if we've reached the limit
                if self.limit and processed_count >= self.limit:
                    break
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error processing file: {str(e)}'))
            raise
        finally:
            progress_bar.close()
        
        # Final summary
        self.stdout.write(self.style.SUCCESS('\n📊 Import Summary:'))
        self.stdout.write(f'📈 Total processed: {processed_count:,}')
        self.stdout.write(f'✅ Created: {created_count:,}')
        self.stdout.write(f'🔄 Updated: {updated_count:,}')
        self.stdout.write(f'⏭️ Skipped: {skipped_count:,}')
        self.stdout.write(f'❌ Errors: {error_count:,}')

    def create_journal_mapping(self):
        """Create mapping of journal titles/ISSNs to Journal objects"""
        journal_map = {}
        
        # Map by ISSN (most reliable)
        for journal in Journal.objects.exclude(issn_linking__isnull=True):
            if journal.issn_linking:
                journal_map[journal.issn_linking] = journal
        
        # Map by electronic ISSN
        for journal in Journal.objects.exclude(issn_electronic__isnull=True):
            if journal.issn_electronic:
                journal_map[journal.issn_electronic] = journal
                
        # Map by print ISSN
        for journal in Journal.objects.exclude(issn_print__isnull=True):
            if journal.issn_print:
                journal_map[journal.issn_print] = journal
        
        # Map by title abbreviation (less reliable but useful)
        for journal in Journal.objects.all():
            if journal.title_abbreviation:
                journal_map[journal.title_abbreviation.lower()] = journal
        
        self.stdout.write(f'📚 Loaded {len(journal_map)} journal mappings')
        return journal_map

    def process_chunk(self, chunk_df, chunk_num, progress_bar):
        """Process a chunk of data"""
        created = 0
        updated = 0
        skipped = 0
        errors = 0
        
        # Clean the chunk data
        chunk_df = chunk_df.replace({np.nan: None})
        
        # Process in smaller batches for database operations
        papers_to_create = []
        papers_to_update = []
        
        for idx, row in chunk_df.iterrows():
            try:
                result = self.process_paper_row(row)
                
                if result['action'] == 'create':
                    papers_to_create.append(result['paper'])
                elif result['action'] == 'update':
                    papers_to_update.append(result['paper'])
                elif result['action'] == 'skip':
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error processing row {idx}: {str(e)}")
                continue
            
            # Update progress for each row
            progress_bar.update(1)
            
            # Batch save when we reach batch size
            if len(papers_to_create) >= self.batch_size:
                if not self.dry_run:
                    Paper.objects.bulk_create(papers_to_create, ignore_conflicts=True)
                created += len(papers_to_create)
                papers_to_create = []
                
            if len(papers_to_update) >= self.batch_size:
                if not self.dry_run:
                    self.bulk_update_papers(papers_to_update)
                updated += len(papers_to_update)
                papers_to_update = []
        
        # Save remaining papers
        if papers_to_create and not self.dry_run:
            Paper.objects.bulk_create(papers_to_create, ignore_conflicts=True)
            created += len(papers_to_create)
            
        if papers_to_update and not self.dry_run:
            self.bulk_update_papers(papers_to_update)
            updated += len(papers_to_update)
        
        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'errors': errors
        }

    def process_paper_row(self, row):
        """Process a single paper row"""
        
        # Clean and validate identifiers
        pmid = self.clean_identifier(row.get('pmid'))
        pmcid = self.clean_identifier(row.get('pmcid'))
        doi = self.clean_identifier(row.get('doi'))
        
        # Must have at least one identifier
        if not any([pmid, pmcid, doi]):
            raise ValueError("No valid identifiers found")
        
        # Generate EPMC ID (use PMID if available, otherwise PMC ID)
        epmc_id = pmid if pmid else pmcid
        if not epmc_id:
            epmc_id = f"DOI_{doi}" if doi else f"UNK_{hash(str(row))}"
        
        # Check if paper already exists
        existing_paper = None
        if pmid:
            existing_paper = Paper.objects.filter(pmid=pmid).first()
        if not existing_paper and pmcid:
            existing_paper = Paper.objects.filter(pmcid=pmcid).first()
        if not existing_paper and doi:
            existing_paper = Paper.objects.filter(doi=doi).first()
        if not existing_paper:
            existing_paper = Paper.objects.filter(epmc_id=epmc_id).first()
            
        # Decide action
        if existing_paper and not self.update_existing:
            return {'action': 'skip', 'paper': None}
        
        # Find or create journal
        journal = self.find_or_create_journal(row)
        
        # Create paper data
        paper_data = self.create_paper_data(row, epmc_id, journal)
        
        if existing_paper:
            # Update existing paper
            for field, value in paper_data.items():
                setattr(existing_paper, field, value)
            existing_paper.transparency_score = existing_paper.calculate_transparency_score()
            existing_paper.transparency_score_pct = existing_paper.get_transparency_percentage()
            existing_paper.transparency_processed = True
            existing_paper.processing_date = timezone.now()
            return {'action': 'update', 'paper': existing_paper}
        else:
            # Create new paper
            paper = Paper(**paper_data)
            paper.transparency_score = paper.calculate_transparency_score()
            paper.transparency_score_pct = paper.get_transparency_percentage()
            paper.transparency_processed = True
            paper.processing_date = timezone.now()
            return {'action': 'create', 'paper': paper}

    def create_paper_data(self, row, epmc_id, journal):
        """Create paper data dictionary from CSV row"""
        
        # Parse publication date
        pub_date = None
        if row.get('firstPublicationDate'):
            pub_date = parse_date(str(row['firstPublicationDate']))
        
        # Extract year from date or use a default
        pub_year = None
        if pub_date:
            pub_year = pub_date.year
        
        return {
            'epmc_id': epmc_id,
            'source': 'MED',  # Default source
            'pmid': self.clean_identifier(row.get('pmid')),
            'pmcid': self.clean_identifier(row.get('pmcid')),
            'doi': self.clean_identifier(row.get('doi')),
            'title': self.clean_text(row.get('title'), max_length=None) or 'Unknown Title',
            'author_string': self.clean_text(row.get('authorString')),
            'journal': journal,
            'journal_title': self.clean_text(row.get('journalTitle'), max_length=500) or 'Unknown Journal',
            'journal_issn': self.clean_text(row.get('journalIssn'), max_length=20),
            'pub_year': pub_year,
            'first_publication_date': pub_date,
            'journal_volume': self.clean_text(row.get('journalVolume'), max_length=50),
            'page_info': self.clean_text(row.get('pageInfo'), max_length=100),
            'issue': self.clean_text(row.get('issue'), max_length=50),
            'pub_type': self.clean_text(row.get('type'), max_length=500),
            'broad_subject_term': self.clean_text(row.get('category'), max_length=200),
            'cited_by_count': self.clean_integer(row.get('citedByCount')) or 0,
            
            # Transparency indicators
            'is_coi_pred': self.clean_boolean(row.get('is_coi_pred')),
            'coi_text': self.clean_text(row.get('coi_text')),
            'is_fund_pred': self.clean_boolean(row.get('is_fund_pred')),
            'fund_text': self.clean_text(row.get('fund_text')),
            'is_register_pred': self.clean_boolean(row.get('is_register_pred')),
            'register_text': self.clean_text(row.get('register_text')),
            'is_open_data': self.clean_boolean(row.get('is_open_data')),
            'open_data_category': self.clean_text(row.get('open_data_category'), max_length=200),
            'open_data_statements': self.clean_text(row.get('open_data_statements')),
            'is_open_code': self.clean_boolean(row.get('is_open_code')),
            'open_code_statements': self.clean_text(row.get('open_code_statements')),
            
            # Default open access to False (will be determined by other means)
            'is_open_access': False,
        }

    def find_or_create_journal(self, row):
        """Find or create journal from row data"""
        journal_issn = self.clean_text(row.get('journalIssn'), max_length=20)
        journal_title = self.clean_text(row.get('journalTitle'), max_length=500)
        
        journal = None
        
        # Try to find by ISSN first
        if journal_issn:
            journal = self.journal_map.get(journal_issn)
        
        # Try to find by title
        if not journal and journal_title:
            journal = self.journal_map.get(journal_title.lower())
        
        # Create journal if not found and creation is enabled
        if not journal and self.create_journals and journal_title:
            journal = Journal(
                title_abbreviation=journal_title[:200],
                title_full=journal_title,
                issn_electronic=journal_issn,
                publisher=self.clean_text(row.get('publisher'), max_length=500),
                broad_subject_terms=self.clean_text(row.get('category'), max_length=200) or ''
            )
            if not self.dry_run:
                journal.save()
                # Add to mapping for future use
                if journal_issn:
                    self.journal_map[journal_issn] = journal
                if journal_title:
                    self.journal_map[journal_title.lower()] = journal
        
        return journal

    def bulk_update_papers(self, papers):
        """Bulk update papers using raw SQL for efficiency"""
        if not papers:
            return
            
        # Use bulk_update for efficiency
        Paper.objects.bulk_update(papers, [
            'pmid', 'pmcid', 'doi', 'title', 'author_string', 'journal_title',
            'journal_issn', 'pub_year', 'first_publication_date', 'journal_volume',
            'page_info', 'issue', 'pub_type', 'broad_subject_term', 'cited_by_count',
            'is_coi_pred', 'coi_text', 'is_fund_pred', 'fund_text', 'is_register_pred',
            'register_text', 'is_open_data', 'open_data_category', 'open_data_statements',
            'is_open_code', 'open_code_statements', 'transparency_score',
            'transparency_score_pct', 'transparency_processed', 'processing_date'
        ])

    # Utility methods
    def get_total_rows(self):
        """Get total number of rows in CSV file"""
        try:
            with open(self.csv_file, 'r') as f:
                return sum(1 for line in f) - 1  # Subtract header
        except Exception:
            return 0

    def check_memory_usage(self):
        """Check if memory usage exceeds limit"""
        memory_percent = psutil.virtual_memory().percent
        return memory_percent > self.memory_limit

    def clean_identifier(self, value):
        """Clean identifier fields"""
        if pd.isna(value) or value is None:
            return None
        value = str(value).strip()
        return value if value and value.lower() not in ['', 'null', 'none', 'nan'] else None

    def clean_text(self, value, max_length=None):
        """Clean text fields"""
        if pd.isna(value) or value is None:
            return None
        
        text = str(value).strip()
        if not text or text.lower() in ['', 'null', 'none', 'nan']:
            return None
            
        if max_length and len(text) > max_length:
            text = text[:max_length]
            
        return text

    def clean_boolean(self, value):
        """Clean boolean fields"""
        if pd.isna(value) or value is None:
            return False
        
        if isinstance(value, bool):
            return value
            
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 't', 'y']
            
        if isinstance(value, (int, float)):
            return bool(value)
            
        return False

    def clean_integer(self, value):
        """Clean integer fields"""
        if pd.isna(value) or value is None:
            return None
        
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None 