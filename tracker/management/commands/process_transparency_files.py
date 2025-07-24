import os
import logging
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import Paper
from django.db import transaction
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process transparency results files and update paper records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file to process',
        )
        parser.add_argument(
            '--directory',
            type=str,
            default=getattr(settings, 'TRANSPARENCY_DATA_DIR', '/home/ost/transparency_results'),
            help='Directory to scan for transparency files',
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
            files_to_process = self.find_unprocessed_files(directory)
        
        if not files_to_process:
            self.stdout.write(
                self.style.WARNING("No unprocessed transparency files found")
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
                    self.process_transparency_file(file_path)
                    self.mark_file_as_processed(file_path)
                    
                logger.info(f"Successfully processed: {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {file_path}: {str(e)}")
                )

    def find_unprocessed_files(self, directory):
        """Find transparency files that haven't been processed yet"""
        if not os.path.exists(directory):
            self.stdout.write(
                self.style.ERROR(f"Directory does not exist: {directory}")
            )
            return []
            
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        processed_files = set()
        if os.path.exists(processed_files_log):
            with open(processed_files_log, 'r') as f:
                processed_files = set(line.strip() for line in f)
        
        all_files = []
        for filename in os.listdir(directory):
            if filename.endswith('.csv') and filename.startswith('transparency_'):
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
            
            # Check for ID columns
            id_columns = [col for col in ['pmid', 'pmcid', 'epmc_id'] if col in df.columns]
            if id_columns:
                self.stdout.write(
                    self.style.SUCCESS(f"  - ID columns found: {id_columns}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("  - No ID columns found (pmid, pmcid, epmc_id)")
                )
            
            # Check for transparency indicator columns
            transparency_columns = [
                col for col in df.columns 
                if any(indicator in col.lower() for indicator in 
                       ['coi', 'fund', 'register', 'open_data', 'open_code'])
            ]
            if transparency_columns:
                self.stdout.write(
                    self.style.SUCCESS(f"  - Transparency columns: {transparency_columns}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("  - No transparency indicator columns found")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  - Error reading file: {str(e)}")
            )

    def process_transparency_file(self, file_path):
        """Process a single transparency results CSV file"""
        self.stdout.write(f"Processing: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")
        
        # Validate that we have at least one ID column
        id_columns = [col for col in ['pmid', 'pmcid', 'epmc_id'] if col in df.columns]
        if not id_columns:
            raise ValueError("File must contain at least one ID column: pmid, pmcid, or epmc_id")
        
        papers_updated = 0
        papers_not_found = 0
        errors = 0
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Find paper by available IDs
                    paper = None
                    
                    # Try EPMC ID first (most specific)
                    if pd.notna(row.get('epmc_id')) and str(row['epmc_id']).strip():
                        try:
                            paper = Paper.objects.get(epmc_id=str(row['epmc_id']).strip())
                        except Paper.DoesNotExist:
                            pass
                    
                    # Try PMID
                    if not paper and pd.notna(row.get('pmid')) and str(row['pmid']).strip():
                        try:
                            paper = Paper.objects.get(pmid=str(row['pmid']).strip())
                        except Paper.DoesNotExist:
                            pass
                    
                    # Try PMCID
                    if not paper and pd.notna(row.get('pmcid')) and str(row['pmcid']).strip():
                        try:
                            paper = Paper.objects.get(pmcid=str(row['pmcid']).strip())
                        except Paper.DoesNotExist:
                            pass
                    
                    if not paper:
                        papers_not_found += 1
                        continue
                    
                    # Update transparency indicators
                    updated = False
                    
                    # COI Disclosure
                    if 'is_coi_pred' in row and pd.notna(row['is_coi_pred']):
                        paper.is_coi_pred = self.parse_boolean(row['is_coi_pred'])
                        updated = True
                    
                    # Funding Disclosure  
                    if 'is_fund_pred' in row and pd.notna(row['is_fund_pred']):
                        paper.is_fund_pred = self.parse_boolean(row['is_fund_pred'])
                        updated = True
                    
                    # Protocol Registration
                    if 'is_register_pred' in row and pd.notna(row['is_register_pred']):
                        paper.is_register_pred = self.parse_boolean(row['is_register_pred'])
                        updated = True
                    
                    # Open Data
                    if 'is_open_data' in row and pd.notna(row['is_open_data']):
                        paper.is_open_data = self.parse_boolean(row['is_open_data'])
                        updated = True
                    
                    # Open Code
                    if 'is_open_code' in row and pd.notna(row['is_open_code']):
                        paper.is_open_code = self.parse_boolean(row['is_open_code'])
                        updated = True
                    
                    # Update text fields if available
                    if 'coi_text' in row and pd.notna(row['coi_text']):
                        paper.coi_text = str(row['coi_text'])[:1000]
                        updated = True
                    
                    if 'fund_text' in row and pd.notna(row['fund_text']):
                        paper.fund_text = str(row['fund_text'])[:1000]
                        updated = True
                    
                    if 'register_text' in row and pd.notna(row['register_text']):
                        paper.register_text = str(row['register_text'])[:1000]
                        updated = True
                    
                    if 'open_data_statements' in row and pd.notna(row['open_data_statements']):
                        paper.open_data_statements = str(row['open_data_statements'])[:1000]
                        updated = True
                    
                    if 'open_code_statements' in row and pd.notna(row['open_code_statements']):
                        paper.open_code_statements = str(row['open_code_statements'])[:1000]
                        updated = True
                    
                    # Update category fields if available
                    if 'open_data_category' in row and pd.notna(row['open_data_category']):
                        paper.open_data_category = str(row['open_data_category'])[:100]
                        updated = True
                    
                    if updated:
                        # Calculate transparency score (out of 6)
                        score = 0
                        score += 1 if paper.is_open_data else 0
                        score += 1 if paper.is_open_code else 0
                        score += 1 if paper.is_coi_pred else 0
                        score += 1 if paper.is_fund_pred else 0
                        score += 1 if paper.is_register_pred else 0
                        score += 1 if paper.is_open_access else 0
                        
                        paper.transparency_score = score
                        paper.transparency_processed = True
                        paper.processing_date = datetime.now().date()
                        paper.save()
                        papers_updated += 1
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing transparency data for row {index}: {str(e)}")
                    continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {file_path}:\n"
                f"  - Papers updated: {papers_updated}\n"
                f"  - Papers not found: {papers_not_found}\n" 
                f"  - Errors: {errors}"
            )
        )

    def parse_boolean(self, value):
        """Parse various boolean representations"""
        if pd.isna(value):
            return False
        
        str_val = str(value).strip().lower()
        
        # Handle numeric values
        try:
            num_val = float(str_val)
            return num_val > 0
        except ValueError:
            pass
        
        # Handle string values
        return str_val in ['true', 'yes', 'y', '1', 'on']

    def mark_file_as_processed(self, file_path):
        """Mark file as processed in log"""
        directory = os.path.dirname(file_path)
        processed_files_log = os.path.join(directory, '.processed_files.log')
        
        with open(processed_files_log, 'a') as f:
            f.write(f"{file_path}\n") 