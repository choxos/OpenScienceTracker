import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from tracker.models import Journal, Paper
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Flexible import for different transparency CSV formats'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to the CSV file to import')
        parser.add_argument('--format', type=str, choices=['auto', 'epmc', 'basic', 'comprehensive'], 
                          default='auto', help='Format of the CSV file')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
        parser.add_argument('--update-existing', action='store_true', 
                          help='Update existing papers with new data')
        parser.add_argument('--show-columns', action='store_true',
                          help='Show available columns in the CSV file and exit')
        parser.add_argument('--dry-run', action='store_true', help='Preview without importing')

    def handle(self, *args, **options):
        file_path = options['file']
        format_type = options['format']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        show_columns = options['show_columns']

        if show_columns:
            self.stdout.write("Analyzing file to show columns...")
            try:
                df = pd.read_csv(file_path, nrows=1)  # Read only one row to get column names
                self.stdout.write(f"Available columns in {file_path}: {df.columns.tolist()}")
                self.stdout.write("Exiting due to --show-columns option.")
                return
            except Exception as e:
                self.stderr.write(f"Error reading CSV for column analysis: {e}")
                return

        if not os.path.exists(file_path):
            self.stderr.write(f"File not found: {file_path}")
            return

        # Read and analyze the CSV
        self.stdout.write(f"Analyzing file: {file_path}")
        try:
            df = pd.read_csv(file_path, nrows=5)  # Read first 5 rows for analysis
        except Exception as e:
            self.stderr.write(f"Error reading CSV: {e}")
            return

        # Auto-detect format if needed
        if format_type == 'auto':
            format_type = self.detect_format(df.columns.tolist())
            self.stdout.write(f"Auto-detected format: {format_type}")

        # Map format to processor
        processors = {
            'epmc': self.process_epmc_format,
            'basic': self.process_basic_format,  
            'comprehensive': self.process_comprehensive_format,
        }

        if format_type not in processors:
            self.stderr.write(f"Unsupported format: {format_type}")
            return

        # Show format info
        self.show_format_info(df.columns.tolist(), format_type)

        if dry_run:
            self.stdout.write("DRY RUN MODE - No data will be imported")
            return

        # Process the full file
        self.stdout.write(f"Processing {file_path} as {format_type} format...")
        processor = processors[format_type]
        processor(file_path, batch_size, update_existing)

    def detect_format(self, columns):
        """Auto-detect CSV format based on column names"""
        columns_set = set(columns)
        
        # Check for comprehensive format (indicators_all.csv style)
        if 'pmcid_pmc' in columns_set and 'is_data_pred' in columns_set and 'com_specific_db' in columns_set:
            return 'comprehensive'
        
        # Check for EPMC format (transparency_1900_01.csv style)
        elif 'rt_all_is_coi_pred' in columns_set and 'inEPMC' in columns_set:
            return 'epmc'
        
        # Check for basic format (medicaltransparency_opendata.csv style)
        elif 'is_coi_pred' in columns_set and 'pmid' in columns_set and 'com_specific_db' not in columns_set:
            return 'basic'
        
        else:
            return 'basic'  # Default fallback

    def show_format_info(self, columns, format_type):
        """Display information about the detected format"""
        format_info = {
            'epmc': {
                'name': 'EPMC Format (transparency_1900_01.csv style)',
                'description': 'Full EPMC data with rt_all_ prefixed transparency indicators',
                'key_fields': ['id', 'source', 'inEPMC', 'inPMC', 'hasPDF', 'rt_all_is_coi_pred']
            },
            'basic': {
                'name': 'Basic Format (medicaltransparency_opendata.csv style)', 
                'description': 'Simplified transparency indicators without EPMC metadata',
                'key_fields': ['pmid', 'pmcid', 'doi', 'is_coi_pred', 'is_fund_pred']
            },
            'comprehensive': {
                'name': 'Comprehensive Format (indicators_all.csv style)',
                'description': 'Most detailed format with extensive transparency sub-indicators',
                'key_fields': ['pmcid_pmc', 'pmid', 'is_data_pred', 'is_code_pred', 'com_specific_db']
            }
        }

        info = format_info.get(format_type, {})
        self.stdout.write(f"\n=== Format: {info.get('name', format_type)} ===")
        self.stdout.write(f"Description: {info.get('description', 'Unknown format')}")
        
        available_key_fields = [f for f in info.get('key_fields', []) if f in columns]
        self.stdout.write(f"Key fields found: {available_key_fields}")
        self.stdout.write(f"Total columns: {len(columns)}")

    def get_or_create_journal_safe(self, journal_title, journal_issn=None):
        """PostgreSQL-safe journal creation without FOR UPDATE issues"""
        if not journal_title or not str(journal_title).strip():
            return None, False
            
        journal_title = str(journal_title).strip()
        journal_issn = str(journal_issn).strip()[:20] if journal_issn else None
        
        # Try to get existing journal first (outside atomic block)
        try:
            journal = Journal.objects.get(title_full=journal_title)
            return journal, False
        except Journal.DoesNotExist:
            pass
        
        # Create new journal in atomic transaction with proper error handling
        try:
            with transaction.atomic():
                journal = Journal.objects.create(
                    title_full=journal_title,
                    title_abbreviation=journal_title[:100],
                    issn_print=journal_issn,
                )
                return journal, True
        except IntegrityError:
            # Another process created it, get the existing one
            try:
                journal = Journal.objects.get(title_full=journal_title)
                return journal, False
            except Journal.DoesNotExist:
                # If still not found, return None to avoid further errors
                return None, False
        except Exception as e:
            # Log the error and return None to continue processing other rows
            logger.error(f"Error creating journal '{journal_title}': {str(e)}")
            return None, False

    def process_epmc_format(self, file_path, batch_size, update_existing):
        """Process EPMC format (transparency_1900_01.csv style)"""
        self.stdout.write("Processing EPMC format...")
        
        chunk_iter = pd.read_csv(file_path, chunksize=batch_size)
        total_processed = 0
        
        for chunk_num, chunk in enumerate(chunk_iter):
            processed, created, updated, errors = self.process_epmc_chunk(chunk, update_existing)
            total_processed += processed
            
            self.stdout.write(f"Chunk {chunk_num + 1}: {processed} processed, {created} created, {updated} updated, {errors} errors")
        
        self.stdout.write(f"Total processed: {total_processed} papers")

    def process_basic_format(self, file_path, batch_size, update_existing):
        """Process basic format (medicaltransparency_opendata.csv style)"""
        self.stdout.write("Processing basic format...")
        
        chunk_iter = pd.read_csv(file_path, chunksize=batch_size)
        total_processed = 0
        
        for chunk_num, chunk in enumerate(chunk_iter):
            processed, created, updated, errors = self.process_basic_chunk(chunk, update_existing)
            total_processed += processed
            
            self.stdout.write(f"Chunk {chunk_num + 1}: {processed} processed, {created} created, {updated} updated, {errors} errors")
        
        self.stdout.write(f"Total processed: {total_processed} papers")

    def process_comprehensive_format(self, file_path, batch_size, update_existing):
        """Process comprehensive format (indicators_all.csv style)"""
        self.stdout.write("Processing comprehensive format...")
        
        chunk_iter = pd.read_csv(file_path, chunksize=batch_size)
        total_processed = 0
        
        for chunk_num, chunk in enumerate(chunk_iter):
            processed, created, updated, errors = self.process_comprehensive_chunk(chunk, update_existing)
            total_processed += processed
            
            self.stdout.write(f"Chunk {chunk_num + 1}: {processed} processed, {created} created, {updated} updated, {errors} errors")
        
        self.stdout.write(f"Total processed: {total_processed} papers")

    def process_epmc_chunk(self, chunk, update_existing):
        """Process chunk for EPMC format"""
        processed, created, updated, errors = 0, 0, 0, 0  # Initialize counters
        
        for index, row in chunk.iterrows():
            try:
                # Get journal
                journal = None
                if pd.notna(row.get('journalTitle')):
                    journal, _ = self.get_or_create_journal_safe(
                        row['journalTitle'], 
                        row.get('journalIssn')
                    )
                
                # Extract transparency indicators with rt_all_ prefix
                transparency_score = 0
                transparency_fields = {}
                
                if pd.notna(row.get('rt_all_is_coi_pred')):
                    transparency_fields['is_coi_pred'] = bool(row.get('rt_all_is_coi_pred'))
                    if transparency_fields['is_coi_pred']:
                        transparency_score += 1
                
                if pd.notna(row.get('rt_all_is_fund_pred')):
                    transparency_fields['is_fund_pred'] = bool(row.get('rt_all_is_fund_pred'))
                    if transparency_fields['is_fund_pred']:
                        transparency_score += 1
                
                if pd.notna(row.get('rt_all_is_register_pred')):
                    transparency_fields['is_register_pred'] = bool(row.get('rt_all_is_register_pred'))
                    if transparency_fields['is_register_pred']:
                        transparency_score += 1
                
                if pd.notna(row.get('rt_data_is_open_data')):
                    transparency_fields['is_open_data'] = bool(row.get('rt_data_is_open_data'))
                    if transparency_fields['is_open_data']:
                        transparency_score += 1
                
                if pd.notna(row.get('rt_data_is_open_code')):
                    transparency_fields['is_open_code'] = bool(row.get('rt_data_is_open_code'))
                    if transparency_fields['is_open_code']:
                        transparency_score += 1
                
                if pd.notna(row.get('isOpenAccess')):
                    transparency_fields['is_open_access'] = str(row.get('isOpenAccess', 'N')).upper() == 'Y'
                    if transparency_fields['is_open_access']:
                        transparency_score += 1

                paper_data = {
                    'source': str(row.get('source', 'PMC'))[:20],
                    'title': str(row.get('title', ''))[:500],
                    'author_string': str(row.get('authorString', ''))[:1000],
                    'journal': journal,
                    'journal_title': str(row.get('journalTitle', ''))[:200],
                    'journal_issn': str(row.get('journalIssn', ''))[:20] or None,
                    'pub_year': self.extract_year(row.get('pubYear')),
                    'pmid': str(row.get('pmid', ''))[:20] or None,
                    'pmcid': str(row.get('pmcid', ''))[:20] or None,
                    'doi': str(row.get('doi', ''))[:100] or None,
                    'transparency_score': transparency_score,
                    'transparency_processed': True,
                    'assessment_tool': 'rtransparent',
                    'in_epmc': str(row.get('inEPMC', 'N')).upper() == 'Y',
                    'in_pmc': str(row.get('inPMC', 'N')).upper() == 'Y',
                    'has_pdf': str(row.get('hasPDF', 'N')).upper() == 'Y',
                    **transparency_fields
                }

                paper, is_created = self.update_or_create_paper_safe(row['id'], paper_data, update_existing)
                
                # Skip if paper creation/update failed
                if paper is None:
                    errors += 1
                    continue
                
                if is_created:
                    created += 1
                else:
                    updated += 1
                processed += 1
                
            except Exception as e:
                errors += 1
                logger.error(f"Error processing EPMC row {index} with ID {row.get('id', 'unknown')}: {str(e)}")
                continue
        
        return processed, created, updated, errors

    def process_basic_chunk(self, chunk, update_existing):
        """Process chunk for basic format"""
        processed, created, updated, errors = 0, 0, 0, 0  # Initialize counters
        
        for index, row in chunk.iterrows():
            try:
                # Get journal
                journal = None
                if pd.notna(row.get('journalTitle')):
                    journal, _ = self.get_or_create_journal_safe(
                        row['journalTitle'], 
                        row.get('journalIssn')
                    )
                
                # Calculate transparency score
                transparency_score = 0
                transparency_fields = {}
                
                for field in ['is_coi_pred', 'is_fund_pred', 'is_register_pred', 'is_open_data', 'is_open_code']:
                    if pd.notna(row.get(field)):
                        value = bool(row.get(field))
                        transparency_fields[field] = value
                        if value:
                            transparency_score += 1

                paper_data = {
                    'title': str(row.get('title', ''))[:500],
                    'author_string': str(row.get('authorString', ''))[:1000],
                    'journal': journal,
                    'journal_title': str(row.get('journalTitle', ''))[:200],
                    'journal_issn': str(row.get('journalIssn', ''))[:20] or None,
                    'pub_year': self.extract_year(row.get('firstPublicationDate')),
                    'pmid': str(row.get('pmid', ''))[:20] or None,
                    'pmcid': str(row.get('pmcid', ''))[:20] or None,
                    'doi': str(row.get('doi', ''))[:100] or None,
                    'transparency_score': transparency_score,
                    'transparency_processed': True,
                    'assessment_tool': 'rtransparent',
                    **transparency_fields
                }

                # Use PMID as primary identifier for basic format
                identifier = row.get('pmid') or row.get('pmcid') or row.get('doi')
                if not identifier:
                    errors += 1
                    continue

                paper, is_created = self.update_or_create_paper_safe(identifier, paper_data, update_existing)
                
                # Skip if paper creation/update failed
                if paper is None:
                    errors += 1
                    continue
                
                if is_created:
                    created += 1
                else:
                    updated += 1
                processed += 1
                
            except Exception as e:
                errors += 1
                logger.error(f"Error processing basic row {index} with ID {row.get('pmid', 'unknown')}: {str(e)}")
                continue
        
        return processed, created, updated, errors

    def process_comprehensive_chunk(self, chunk, update_existing):
        """Process chunk for comprehensive format (indicators_all.csv)"""
        processed, created, updated, errors = 0, 0, 0, 0  # Initialize counters
        
        for index, row in chunk.iterrows():
            try:
                # Get journal
                journal = None
                if pd.notna(row.get('journal')):
                    journal, _ = self.get_or_create_journal_safe(
                        row['journal'], 
                        None  # No ISSN in this format
                    )
                
                # Calculate transparency score from comprehensive indicators
                transparency_score = 0
                transparency_fields = {}
                
                # Main transparency indicators
                for field in ['is_data_pred', 'is_code_pred', 'is_coi_pred', 'is_fund_pred', 'is_register_pred']:
                    if pd.notna(row.get(field)):
                        value = bool(row.get(field))
                        # Map comprehensive format to our standard field names
                        if field == 'is_data_pred':
                            transparency_fields['is_open_data'] = value
                        elif field == 'is_code_pred':
                            transparency_fields['is_open_code'] = value
                        else:
                            transparency_fields[field] = value
                        
                        if value:
                            transparency_score += 1

                paper_data = {
                    'source': 'rtransparent',
                    'title': self.safe_extract_string(row, ['title', 'Title', 'paper_title'], 'Title not available', 500),
                    'author_string': self.safe_extract_string(row, ['author', 'Author', 'authors', 'authorString'], 'Unknown Author', 1000),
                    'journal': journal,
                    'journal_title': self.safe_extract_string(row, ['journal', 'Journal', 'journalTitle'], '', 200),
                    'pub_year': self.safe_extract_year(row, ['year', 'Year', 'pub_year', 'pubYear']),
                    'pmid': self.safe_extract_string(row, ['pmid', 'PMID'], None, 20),
                    'pmcid': self.safe_extract_string(row, ['pmcid_pmc', 'pmcid', 'PMCID'], None, 20),
                    'doi': self.safe_extract_string(row, ['doi', 'DOI'], None, 100),
                    'transparency_score': transparency_score,
                    'transparency_processed': True,
                    'assessment_tool': 'rtransparent',
                    'pub_type': self.safe_extract_string(row, ['type', 'Type', 'pubType'], None, 100),
                    'broad_subject_term': self.safe_extract_string(row, ['field', 'Field', 'subject'], None, 200),
                    **transparency_fields
                }

                # Use PMCID as primary identifier for comprehensive format
                identifier = row.get('pmcid_pmc') or row.get('pmid') or row.get('doi')
                if not identifier:
                    errors += 1
                    continue

                paper, is_created = self.update_or_create_paper_safe(identifier, paper_data, update_existing)
                
                # Skip if paper creation/update failed
                if paper is None:
                    errors += 1
                    continue
                
                if is_created:
                    created += 1
                else:
                    updated += 1
                processed += 1
                
            except Exception as e:
                errors += 1
                logger.error(f"Error processing comprehensive row {index} with ID {row.get('pmcid_pmc', 'unknown')}: {str(e)}")
                continue
        
        return processed, created, updated, errors

    def update_or_create_paper_safe(self, identifier, paper_data, update_existing):
        """PostgreSQL-safe paper creation without FOR UPDATE issues"""
        identifier = str(identifier).strip()
        
        # Try to get existing paper first (outside atomic block)
        existing_paper = None
        
        # Try by epmc_id first
        if 'epmc_id' in paper_data and paper_data['epmc_id']:
            existing_paper = Paper.objects.filter(epmc_id=paper_data['epmc_id']).first()
        
        # Try by other identifiers if epmc_id didn't work
        if not existing_paper:
            for field_name, field_value in [('pmid', paper_data.get('pmid')), 
                                          ('pmcid', paper_data.get('pmcid')), 
                                          ('doi', paper_data.get('doi'))]:
                if field_value:
                    existing_paper = Paper.objects.filter(**{field_name: field_value}).first()
                    if existing_paper:
                        break
        
        # Update existing paper
        if existing_paper:
            if update_existing:
                try:
                    for field, value in paper_data.items():
                        setattr(existing_paper, field, value)
                    existing_paper.save()
                except Exception as e:
                    logger.error(f"Error updating paper '{identifier}': {str(e)}")
                    return existing_paper, False
            return existing_paper, False
        
        # Create new paper in atomic transaction with proper error handling
        try:
            with transaction.atomic():
                # Set appropriate epmc_id if not already set
                if 'epmc_id' not in paper_data or not paper_data['epmc_id']:
                    if paper_data.get('pmid'):
                        paper_data['epmc_id'] = paper_data['pmid']
                    elif paper_data.get('pmcid'):
                        paper_data['epmc_id'] = paper_data['pmcid']
                    else:
                        paper_data['epmc_id'] = identifier
                
                paper = Paper.objects.create(**paper_data)
                return paper, True
        except IntegrityError:
            # Another process created it, try to get the existing one
            existing_paper = Paper.objects.filter(epmc_id=paper_data['epmc_id']).first()
            if existing_paper:
                if update_existing:
                    try:
                        for field, value in paper_data.items():
                            setattr(existing_paper, field, value)
                        existing_paper.save()
                    except Exception as e:
                        logger.error(f"Error updating paper after IntegrityError '{identifier}': {str(e)}")
                return existing_paper, False
            else:
                # If still not found, return None to avoid further errors
                logger.error(f"Paper with epmc_id '{paper_data['epmc_id']}' not found after creation attempt")
                return None, False
        except Exception as e:
            # Log the error and return None to continue processing other rows
            logger.error(f"Error creating paper '{identifier}': {str(e)}")
            return None, False

    def extract_year(self, date_value):
        """Extract year from various date formats"""
        if pd.isna(date_value):
            return None
        
        try:
            date_str = str(date_value).strip()
            if len(date_str) >= 4:
                year = int(date_str[:4])
                if 1800 <= year <= 2100:
                    return year
        except (ValueError, TypeError):
            pass
        
        return None 

    def safe_extract_string(self, row, field_names, default_value="", max_length=None):
        """Safely extract string value from row, trying multiple field names"""
        if isinstance(field_names, str):
            field_names = [field_names]
        
        for field_name in field_names:
            value = row.get(field_name)
            if pd.notna(value) and str(value).strip() and str(value).strip().lower() not in ['nan', 'null', 'none', 'n/a']:
                clean_value = str(value).strip()
                if max_length:
                    return clean_value[:max_length]
                return clean_value
        
        return default_value or None

    def safe_extract_year(self, row, field_names):
        """Safely extract year from row, trying multiple field names"""
        if isinstance(field_names, str):
            field_names = [field_names]
        
        for field_name in field_names:
            value = row.get(field_name)
            if pd.notna(value):
                year = self.extract_year(value)
                if year:
                    return year
        
        return None 