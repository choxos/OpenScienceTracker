import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date
from tracker.models import Paper, Journal
from datetime import datetime

class Command(BaseCommand):
    help = 'Import EuropePMC data from epmc_db_[year]_[month].csv files'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the EuropePMC CSV file (e.g., epmc_db_1900_01.csv)'
        )
        parser.add_argument(
            '--folder',
            type=str,
            help='Path to folder containing multiple CSV files (imports all files matching pattern)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing records if EuropePMC ID already exists',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.update_existing = options['update_existing']
        self.batch_size = options['batch_size']
        
        if options['folder']:
            self.import_folder(options['folder'])
        else:
            self.import_file(options['csv_file'])

    def import_folder(self, folder_path):
        """Import all EPMC CSV files from a folder"""
        if not os.path.exists(folder_path):
            raise CommandError(f'Folder does not exist: {folder_path}')
        
        # Find all files matching pattern epmc_db_*.csv
        csv_files = []
        for filename in os.listdir(folder_path):
            if filename.startswith('epmc_db_') and filename.endswith('.csv'):
                csv_files.append(os.path.join(folder_path, filename))
        
        if not csv_files:
            raise CommandError(f'No epmc_db_*.csv files found in folder: {folder_path}')
        
        csv_files.sort()  # Process in chronological order
        self.stdout.write(f"📁 Found {len(csv_files)} CSV files to import")
        
        total_imported = 0
        total_updated = 0
        
        for csv_file in csv_files:
            self.stdout.write(f"\n📄 Processing: {os.path.basename(csv_file)}")
            imported, updated = self.import_file(csv_file)
            total_imported += imported
            total_updated += updated
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Folder import complete!\n"
                f"   📊 Total imported: {total_imported:,} papers\n"
                f"   🔄 Total updated: {total_updated:,} papers\n"
                f"   📁 Files processed: {len(csv_files)}"
            )
        )

    def import_file(self, csv_file):
        """Import a single EuropePMC CSV file"""
        if not os.path.exists(csv_file):
            raise CommandError(f'File does not exist: {csv_file}')

        self.stdout.write(f"📚 Loading EuropePMC data from: {csv_file}")
        
        try:
            # Load CSV with pandas
            df = pd.read_csv(csv_file)
            total_rows = len(df)
            self.stdout.write(f"📄 Found {total_rows:,} records in CSV")
            
            # Validate required columns
            required_cols = ['id', 'source', 'title', 'journalTitle', 'pubYear']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise CommandError(f'Missing required columns: {missing_cols}')
            
            # Clean and prepare data
            df = self.clean_dataframe(df)
            
            if self.dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"🔍 DRY RUN: Would process {len(df):,} records\n"
                        f"   Sample data:\n{df[['id', 'title', 'journalTitle', 'pubYear']].head(3).to_string()}"
                    )
                )
                return 0, 0
            
            # Import data in batches
            imported_count, updated_count = self.process_dataframe(df)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Import complete!\n"
                    f"   📊 Imported: {imported_count:,} new papers\n"
                    f"   🔄 Updated: {updated_count:,} existing papers\n"
                    f"   📁 File: {os.path.basename(csv_file)}"
                )
            )
            
            return imported_count, updated_count
            
        except Exception as e:
            raise CommandError(f'Error processing CSV file: {str(e)}')

    def clean_dataframe(self, df):
        """Clean and standardize the dataframe"""
        # Replace NaN values with None/empty strings appropriately
        df = df.where(pd.notnull(df), None)
        
        # Convert boolean columns
        bool_columns = [
            'isOpenAccess', 'inEPMC', 'inPMC', 'hasPDF', 'hasBook', 'hasSuppl',
            'hasReferences', 'hasTextMinedTerms', 'hasDbCrossReferences', 
            'hasLabsLinks', 'hasTMAccessionNumbers'
        ]
        
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].map({'Y': True, 'N': False, True: True, False: False}).fillna(False)
        
        # Convert integer columns
        int_columns = ['pubYear', 'citedByCount']
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Clean text columns
        text_columns = ['title', 'journalTitle', 'authorString', 'pubType', 'pageInfo']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
        
        return df

    def process_dataframe(self, df):
        """Process dataframe in batches"""
        imported_count = 0
        updated_count = 0
        
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            self.stdout.write(f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_df)} records)")
            
            with transaction.atomic():
                for _, row in batch_df.iterrows():
                    try:
                        paper, created = self.create_or_update_paper(row)
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1
                            
                        # Progress indicator
                        if (imported_count + updated_count) % 100 == 0:
                            self.stdout.write(f"   📊 Processed: {imported_count + updated_count:,} papers", ending='\r')
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error processing record {row.get('id', 'unknown')}: {str(e)}")
                        )
                        continue
        
        return imported_count, updated_count

    def create_or_update_paper(self, row):
        """Create or update a Paper instance from CSV row"""
        epmc_id = str(row['id'])
        
        # Check if paper already exists
        if self.update_existing:
            paper, created = Paper.objects.get_or_create(
                epmc_id=epmc_id,
                defaults=self.get_paper_data(row)
            )
            if not created:
                # Update existing paper
                for field, value in self.get_paper_data(row).items():
                    setattr(paper, field, value)
                paper.save()
        else:
            # Only create new papers
            paper, created = Paper.objects.get_or_create(
                epmc_id=epmc_id,
                defaults=self.get_paper_data(row)
            )
        
        return paper, created

    def get_paper_data(self, row):
        """Extract paper data from CSV row"""
        # Parse dates
        first_index_date = None
        first_publication_date = None
        
        if row.get('firstIndexDate'):
            try:
                first_index_date = parse_date(str(row['firstIndexDate']))
            except:
                pass
                
        if row.get('firstPublicationDate'):
            try:
                first_publication_date = parse_date(str(row['firstPublicationDate']))
            except:
                pass

        # Ensure string fields are properly handled
        def safe_str(value, max_length=None):
            if value is None or value == 'nan':
                return ''
            result = str(value).strip()
            if max_length and len(result) > max_length:
                result = result[:max_length]
            return result

        def safe_int(value, default=0):
            try:
                return int(value) if value is not None and str(value) != 'nan' else default
            except:
                return default

        def safe_bool(value):
            if isinstance(value, bool):
                return value
            return str(value).upper() == 'Y' if value else False

        return {
            'source': safe_str(row.get('source'), 20),
            'pmcid': safe_str(row.get('pmcid'), 20) or None,
            'pmid': safe_str(row.get('pmid'), 20) or None,
            'doi': safe_str(row.get('doi'), 200) or None,
            'title': safe_str(row.get('title')),
            'author_string': safe_str(row.get('authorString')) or None,
            'journal_title': safe_str(row.get('journalTitle'), 500),
            'journal_issn': safe_str(row.get('journalIssn'), 20) or None,
            'pub_year': safe_int(row.get('pubYear')),
            'issue': safe_str(row.get('issue'), 50) or None,
            'journal_volume': safe_str(row.get('journalVolume'), 50) or None,
            'page_info': safe_str(row.get('pageInfo'), 100) or None,
            'pub_type': safe_str(row.get('pubType'), 500) or None,
            'first_index_date': first_index_date,
            'first_publication_date': first_publication_date,
            'is_open_access': safe_bool(row.get('isOpenAccess')),
            'in_epmc': safe_bool(row.get('inEPMC')),
            'in_pmc': safe_bool(row.get('inPMC')),
            'has_pdf': safe_bool(row.get('hasPDF')),
            'has_book': safe_bool(row.get('hasBook')),
            'has_suppl': safe_bool(row.get('hasSuppl')),
            'has_references': safe_bool(row.get('hasReferences')),
            'has_text_mined_terms': safe_bool(row.get('hasTextMinedTerms')),
            'has_db_cross_references': safe_bool(row.get('hasDbCrossReferences')),
            'has_labs_links': safe_bool(row.get('hasLabsLinks')),
            'has_tm_accession_numbers': safe_bool(row.get('hasTMAccessionNumbers')),
            'cited_by_count': safe_int(row.get('citedByCount')),
        } 