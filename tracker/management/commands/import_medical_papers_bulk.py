from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal
import pandas as pd
import os
from django.utils import timezone
from datetime import datetime
from tqdm import tqdm
import psutil
import gc

class Command(BaseCommand):
    help = 'Bulk import medical transparency papers with progress tracking (respects Django defaults)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process per batch (default: 500)'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=None,
            help='Maximum number of records to import (for testing)'
        )
        parser.add_argument(
            '--skip-rows',
            type=int,
            default=0,
            help='Number of rows to skip at the beginning (for resuming)'
        )

    def handle(self, *args, **options):
        # Check environment (support both Railway and Hetzner)
        is_production = (
            os.environ.get('RAILWAY_ENVIRONMENT') or 
            os.environ.get('PRODUCTION') or 
            os.path.exists('/var/www/ost')
        )
        
        if not is_production:
            self.stdout.write(self.style.WARNING('⚠️  Not in production environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🏥 Bulk importing medical transparency papers...'))
        
        # Check if already imported
        existing_papers = Paper.objects.count()
        if existing_papers > 100000:
            self.stdout.write(self.style.WARNING(f'✅ Large number of papers already imported ({existing_papers:,} found). Continue? (y/N)'))
            # For automated deployment, we'll continue automatically
            
        # Look for the medical data file
        csv_files = [
            'rtransparent_csvs/medicaltransparency_opendata.csv',
            'medicaltransparency_opendata.csv',
            'medical_transparency_data.csv'
        ]
        
        csv_file = None
        for file_path in csv_files:
            if os.path.exists(file_path):
                csv_file = file_path
                break
        
        if not csv_file:
            self.stdout.write(self.style.ERROR('❌ Medical transparency CSV file not found'))
            self.stdout.write('💡 Looking for files:')
            for f in csv_files:
                self.stdout.write(f'   - {f}')
            return
        
        try:
            # Get file size and estimate processing time
            file_size = os.path.getsize(csv_file) / (1024 * 1024)  # MB
            self.stdout.write(f"📄 Processing file: {csv_file} ({file_size:.1f} MB)")
            
            # Read CSV with optimized settings for large files
            self.stdout.write("📥 Loading CSV data (this may take a few minutes)...")
            
            # Use chunked reading for memory efficiency
            chunk_size = 50000  # Read 50k rows at a time
            batch_size = options['batch_size']
            max_records = options['max_records']
            skip_rows = options['skip_rows']
            
            # Pre-load journal mapping for efficient lookup
            self.stdout.write("📚 Building journal mapping...")
            journal_map = self.build_journal_mapping()
            self.stdout.write(f"📚 Built journal mapping with {len(journal_map)} journals")
            
            # Process file in chunks
            total_imported = 0
            total_processed = 0
            chunk_num = 0
            
            # Get total rows for progress tracking (approximate)
            self.stdout.write("🔢 Estimating total rows...")
            total_rows = self.estimate_total_rows(csv_file)
            if max_records:
                total_rows = min(total_rows, max_records)
            self.stdout.write(f"📊 Estimated {total_rows:,} total rows to process")
            
            # Process CSV in chunks
            progress_bar = tqdm(total=total_rows, desc="Processing medical papers", unit="rows")
            
            for chunk_df in pd.read_csv(
                csv_file, 
                chunksize=chunk_size,
                low_memory=False,
                skiprows=range(1, skip_rows + 1) if skip_rows > 0 else None
            ):
                chunk_num += 1
                
                # Apply max_records limit
                if max_records and total_processed + len(chunk_df) > max_records:
                    chunk_df = chunk_df.head(max_records - total_processed)
                
                # Process this chunk
                imported_count = self.process_chunk(
                    chunk_df, journal_map, batch_size, chunk_num, progress_bar
                )
                
                total_imported += imported_count
                total_processed += len(chunk_df)
                
                # Memory cleanup
                del chunk_df
                gc.collect()
                
                # Memory monitoring
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                self.stdout.write(f"  💾 Memory usage: {memory_usage:.1f} MB")
                
                # Break if we've reached max_records
                if max_records and total_processed >= max_records:
                    break
            
            progress_bar.close()
            
            # Report results
            total_papers = Paper.objects.count()
            medical_papers = Paper.objects.filter(
                assessment_tool__icontains='rtransparent'
            ).count()
            
            self.stdout.write(self.style.SUCCESS('✅ Medical bulk import completed!'))
            self.stdout.write(f'📊 Total papers in database: {total_papers:,}')
            self.stdout.write(f'🏥 Medical papers imported: {total_imported:,}')
            self.stdout.write(f'📈 Records processed: {total_processed:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File {csv_file} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}'))
    
    def estimate_total_rows(self, csv_file):
        """Estimate total rows in CSV for progress tracking"""
        try:
            # Quick estimation by reading first chunk and file size
            sample_chunk = pd.read_csv(csv_file, nrows=1000)
            file_size = os.path.getsize(csv_file)
            avg_row_size = file_size / len(sample_chunk) if len(sample_chunk) > 0 else 1000
            estimated_rows = int(file_size / avg_row_size * 1000 / len(sample_chunk))
            return estimated_rows
        except:
            return 3000000  # Default estimate for medical data
    
    def process_chunk(self, chunk_df, journal_map, batch_size, chunk_num, progress_bar):
        """Process a chunk of data"""
        # Clean data
        chunk_df = chunk_df.fillna('')
        chunk_df = chunk_df.where(pd.notnull(chunk_df), None)
        
        # Convert to model instances in batches
        papers = []
        imported_count = 0
        
        chunk_progress = tqdm(
            chunk_df.iterrows(), 
            desc=f"Chunk {chunk_num}", 
            total=len(chunk_df),
            leave=False,
            unit="rows"
        )
        
        for idx, row in chunk_progress:
            try:
                # Find the correct journal ID
                journal_id = self.find_journal_id(row, journal_map)
                
                # Create Paper instance - Django will apply model defaults
                paper = Paper(
                    pmid=self.clean_varchar(row.get('pmid'), 20),
                    pmcid=self.clean_varchar(row.get('pmcid'), 20),
                    doi=self.clean_field(row.get('doi')),
                    title=self.clean_field(row.get('title')) or 'Unknown Title',
                    author_string=self.clean_field(row.get('authorString')),
                    journal_title=self.clean_field(row.get('journalTitle')) or 'Unknown Journal',
                    journal_issn=self.clean_issn(row.get('journalIssn')),
                    pub_year=self.clean_year(row.get('pubYear')) or 2020,
                    first_publication_date=self.clean_date(row.get('firstPublicationDate')),
                    year_first_pub=self.clean_year(row.get('pubYear')),
                    month_first_pub=self.clean_number(row.get('pubMonth')),
                    journal_volume=self.clean_varchar(row.get('journalVolume'), 20),
                    page_info=self.clean_varchar(row.get('pageInfo'), 50),
                    issue=self.clean_varchar(row.get('issue'), 20),
                    pub_type=self.clean_varchar(row.get('pubTypeList'), 200),
                    
                    # Transparency indicators (Django will handle defaults)
                    is_coi_pred=self.clean_boolean(row.get('is_coi_pred')),
                    is_fund_pred=self.clean_boolean(row.get('is_fund_pred')),
                    is_register_pred=self.clean_boolean(row.get('is_register_pred')),
                    is_open_data=self.clean_boolean(row.get('is_open_data')),
                    is_open_code=self.clean_boolean(row.get('is_open_code')),
                    is_replication=self.clean_boolean(row.get('is_replication')),
                    is_novelty=self.clean_boolean(row.get('is_novelty')),
                    
                    transparency_score=self.clean_number(row.get('transparency_score')) or 0,
                    transparency_score_pct=self.clean_float(row.get('transparency_score_pct')) or 0.0,
                    
                    # Assessment metadata
                    assessment_tool=self.clean_field(row.get('assessment_tool')) or 'rtransparent',
                    ost_version=self.clean_field(row.get('ost_version')) or '1.0',
                    assessment_date=self.clean_date_tz(row.get('assessment_date')),
                    
                    # Subject classification
                    broad_subject_category=self.clean_field(row.get('meshMajor')),
                    
                    # Journal reference (properly mapped)
                    journal_id=journal_id,
                )
                papers.append(paper)
                
                # Batch insert when reaching batch_size
                if len(papers) >= batch_size:
                    with transaction.atomic():
                        Paper.objects.bulk_create(papers, ignore_conflicts=True)
                    imported_count += len(papers)
                    papers = []
                    
                    # Update chunk progress
                    chunk_progress.set_postfix(imported=imported_count)
                
            except Exception as e:
                # Skip problematic rows but continue processing
                chunk_progress.set_postfix(error=str(e)[:30])
                continue
        
        # Insert remaining papers
        if papers:
            with transaction.atomic():
                Paper.objects.bulk_create(papers, ignore_conflicts=True)
            imported_count += len(papers)
        
        chunk_progress.close()
        progress_bar.update(len(chunk_df))
        
        return imported_count
    
    def build_journal_mapping(self):
        """Build efficient journal lookup mapping"""
        journal_map = {}
        
        # Get all journals from database
        journals = Journal.objects.all().values('id', 'nlm_id', 'title_abbreviation', 'title_full', 'issn_print', 'issn_electronic')
        
        for journal in journals:
            j_id = journal['id']
            
            # Map by NLM ID (most reliable)
            if journal['nlm_id']:
                journal_map[f"nlm:{journal['nlm_id']}"] = j_id
            
            # Map by title abbreviation
            if journal['title_abbreviation']:
                journal_map[f"title:{journal['title_abbreviation'].lower()}"] = j_id
            
            # Map by title full
            if journal['title_full']:
                journal_map[f"title:{journal['title_full'].lower()}"] = j_id
            
            # Map by ISSN
            if journal['issn_print']:
                journal_map[f"issn:{journal['issn_print']}"] = j_id
            if journal['issn_electronic']:
                journal_map[f"issn:{journal['issn_electronic']}"] = j_id
        
        return journal_map
    
    def find_journal_id(self, row, journal_map):
        """Find the correct journal ID for a paper"""
        # Try journal title first for medical data
        journal_title = self.clean_field(row.get('journalTitle'))
        if journal_title:
            key = f"title:{journal_title.lower()}"
            if key in journal_map:
                return journal_map[key]
        
        # Try ISSN
        journal_issn = self.clean_field(row.get('journalIssn'))
        if journal_issn:
            # Handle multiple ISSNs separated by semicolons
            issns = [issn.strip() for issn in journal_issn.split(';') if issn.strip()]
            for issn in issns:
                key = f"issn:{issn}"
                if key in journal_map:
                    return journal_map[key]
        
        # Fallback: return the first journal ID if no match found
        if journal_map:
            first_journal_id = min(journal_map.values())
            return first_journal_id
        
        # Last resort: create a default journal and return its ID
        default_journal, created = Journal.objects.get_or_create(
            title_abbreviation='Unknown Journal',
            defaults={
                'title_full': 'Unknown Journal',
                'broad_subject_terms': 'General',
                'subject_term_count': 1,
            }
        )
        return default_journal.id
    
    def clean_field(self, value):
        """Clean field value"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        return str(value).strip()
    
    def clean_boolean(self, value):
        """Clean boolean value"""
        if pd.isna(value) or value == "nan" or value == "":
            return False
        return str(value).upper() in ['TRUE', '1', 'YES', 'T', 'Y']
    
    def clean_year(self, value):
        """Clean year field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            year = int(float(value))
            if 1800 <= year <= 2030:
                return year
        except (ValueError, TypeError):
            pass
        return None
    
    def clean_number(self, value):
        """Clean number field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def clean_float(self, value):
        """Clean float field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def clean_varchar(self, value, max_length):
        """Clean varchar field with length limit"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        text = str(value).strip()
        # Truncate to max_length if longer
        return text[:max_length] if len(text) > max_length else text
    
    def clean_issn(self, value):
        """Clean ISSN field (max 9 chars)"""
        return self.clean_varchar(value, 9)
    
    def clean_date_tz(self, value):
        """Clean date field with timezone awareness"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            dt = pd.to_datetime(value, errors='coerce')
            if dt is not None and not pd.isna(dt):
                # Make timezone-aware if naive
                if dt.tzinfo is None:
                    return timezone.make_aware(dt, timezone.get_current_timezone())
                return dt
        except:
            pass
        return None
    
    def clean_date(self, value):
        """Clean date field"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            return pd.to_datetime(value, errors='coerce')
        except:
            return None 