import os
import logging
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import Journal, Paper
from datetime import datetime
from django.db import transaction, IntegrityError
import sys

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process EPMC data files and import into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file to process',
        )
        parser.add_argument(
            '--directory',
            type=str,
            default=getattr(settings, 'EPMC_DATA_DIR', '/home/xeradb/epmc_monthly_data'),
            help='Directory to scan for EPMC files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        directory = options['directory']
        specific_file = options['file']
        dry_run = options['dry_run']
        
        if specific_file:
            files_to_process = [specific_file]
        else:
            # Find all CSV files that haven't been processed
            files_to_process = self.find_unprocessed_files(directory)
        
        if not files_to_process:
            self.stdout.write(
                self.style.WARNING("No unprocessed EPMC files found")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"Found {len(files_to_process)} file(s) to process")
        )
        
        for file_path in files_to_process:
            try:
                self.stdout.write(f"Processing: {file_path}")
                
                if dry_run:
                    self.dry_run_file(file_path)
                else:
                    self.process_epmc_file(file_path)
                    self.mark_file_as_processed(file_path)
                    
                logger.info(f"Successfully processed: {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {file_path}: {str(e)}")
                )

    def find_unprocessed_files(self, directory):
        """Find CSV files that haven't been processed yet"""
        if not os.path.exists(directory):
            self.stdout.write(
                self.style.ERROR(f"Directory does not exist: {directory}")
            )
            return []
            
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        # Load list of already processed files
        processed_files = set()
        if os.path.exists(processed_files_log):
            with open(processed_files_log, 'r') as f:
                processed_files = set(line.strip() for line in f)
        
        # Find all CSV files
        all_files = []
        for filename in os.listdir(directory):
            if filename.endswith('.csv') and (filename.startswith('epmc_') or filename.startswith('epmc_db_')):
                file_path = os.path.join(directory, filename)
                if file_path not in processed_files:
                    all_files.append(file_path)
        
        return sorted(all_files)

    def dry_run_file(self, file_path):
        """Show what would be processed without making changes"""
        self.stdout.write(f"DRY RUN: Would process {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            self.stdout.write(f"  - File contains {len(df)} rows")
            self.stdout.write(f"  - Columns: {', '.join(df.columns)}")
            
            # Check required columns
            required_columns = ['id', 'source', 'title', 'authorString', 'journalTitle']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.stdout.write(
                    self.style.WARNING(f"  - Missing columns: {missing_columns}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("  - All required columns present")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  - Error reading file: {str(e)}")
            )

    def get_or_create_journal_safe(self, journal_title, journal_issn=None):
        """PostgreSQL-safe journal creation without FOR UPDATE issues"""
        if not journal_title or not journal_title.strip():
            return None, False
            
        journal_title = str(journal_title).strip()
        journal_issn = str(journal_issn).strip() if journal_issn else None
        
        # Try to get existing journal first
        try:
            journal = Journal.objects.get(title_full=journal_title)
            return journal, False
        except Journal.DoesNotExist:
            pass
        
        # Create new journal in atomic transaction
        with transaction.atomic():
            try:
                journal = Journal.objects.create(
                    title_full=journal_title,
                    title_abbreviation=journal_title[:50] if len(journal_title) > 50 else journal_title,
                    issn_print=journal_issn,
                )
                return journal, True
            except IntegrityError:
                # Another process created it, get the existing one
                journal = Journal.objects.get(title_full=journal_title)
                return journal, False

    def update_or_create_paper_safe(self, epmc_id, paper_data):
        """PostgreSQL-safe paper creation without FOR UPDATE issues"""
        epmc_id = str(epmc_id).strip()
        
        # Try to get existing paper first
        try:
            paper = Paper.objects.get(epmc_id=epmc_id)
            # Update existing paper
            for field, value in paper_data.items():
                setattr(paper, field, value)
            paper.save()
            return paper, False
        except Paper.DoesNotExist:
            pass
        
        # Create new paper in atomic transaction
        with transaction.atomic():
            try:
                paper = Paper.objects.create(epmc_id=epmc_id, **paper_data)
                return paper, True
            except IntegrityError:
                # Another process created it, update the existing one
                paper = Paper.objects.get(epmc_id=epmc_id)
                for field, value in paper_data.items():
                    setattr(paper, field, value)
                paper.save()
                return paper, False

    def process_epmc_file(self, file_path):
        """Process a single EPMC CSV file"""
        self.stdout.write(f"Processing: {file_path}")
        
        # Read CSV file
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")
        
        # Validate required columns
        required_columns = ['id', 'source', 'title', 'authorString', 'journalTitle']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Process each row
        papers_created = 0
        papers_updated = 0
        journals_created = 0
        errors = 0
        
        for index, row in df.iterrows():
            try:
                # Get or create journal using PostgreSQL-safe method
                journal = None
                if pd.notna(row.get('journalTitle')) and row.get('journalTitle').strip():
                    journal_title = str(row['journalTitle']).strip()
                    journal_issn = str(row.get('journalIssn', '')).strip() or None
                    journal, journal_created = self.get_or_create_journal_safe(
                        journal_title, journal_issn
                    )
                    if journal_created:
                        journals_created += 1
                
                # Prepare paper data
                paper_data = {
                    'source': str(row.get('source', 'PMC')).strip()[:20],
                    'title': str(row.get('title', '')).strip()[:500],  # Truncate if too long
                    'author_string': str(row.get('authorString', '')).strip()[:1000],
                    'journal': journal,
                    'journal_title': str(row.get('journalTitle', '')).strip()[:200],
                    'journal_issn': str(row.get('journalIssn', '')).strip()[:20] or None,
                    'pub_year': self.extract_year(row.get('firstPublicationDate')),
                    'pmid': str(row.get('pmid', '')).strip() or None,
                    'pmcid': str(row.get('pmcid', '')).strip() or None,
                    'doi': str(row.get('doi', '')).strip() or None,
                    'is_open_access': str(row.get('isOpenAccess', 'N')).upper() == 'Y',
                    'in_epmc': str(row.get('inEPMC', 'N')).upper() == 'Y',
                    'in_pmc': str(row.get('inPMC', 'N')).upper() == 'Y',
                    'has_pdf': str(row.get('hasPDF', 'N')).upper() == 'Y',
                    'first_publication_date': self.parse_date(row.get('firstPublicationDate')),
                    'first_index_date': self.parse_date(row.get('firstIndexDate')),
                    'pub_type': str(row.get('pubType', '')).strip()[:100] or None,
                }
                
                # Create or update paper using PostgreSQL-safe method
                paper, created = self.update_or_create_paper_safe(
                    row['id'], paper_data
                )
                
                if created:
                    papers_created += 1
                else:
                    papers_updated += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error processing row {index} with ID {row.get('id', 'unknown')}: {str(e)}")
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {file_path}:\n"
                f"  - Papers created: {papers_created}\n"
                f"  - Papers updated: {papers_updated}\n"
                f"  - Journals created: {journals_created}\n"
                f"  - Errors: {errors}"
            )
        )

    def extract_year(self, date_string):
        """Extract year from date string"""
        if pd.isna(date_string) or not str(date_string).strip():
            return None
        try:
            date_str = str(date_string).strip()
            # Try to extract year from various date formats
            if len(date_str) >= 4:
                year = int(date_str[:4])
                # Validate year range
                if 1800 <= year <= 2100:
                    return year
            return None
        except (ValueError, TypeError):
            return None

    def parse_date(self, date_string):
        """Parse date string to datetime object"""
        if pd.isna(date_string) or not str(date_string).strip():
            return None
        try:
            date_str = str(date_string).strip()
            # Try various date formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str[:len(fmt)], fmt).date()
                except ValueError:
                    continue
            return None
        except (ValueError, TypeError):
            return None

    def mark_file_as_processed(self, file_path):
        """Mark file as processed in log"""
        directory = os.path.dirname(file_path)
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        with open(processed_files_log, 'a') as f:
            f.write(f"{file_path}\n") 