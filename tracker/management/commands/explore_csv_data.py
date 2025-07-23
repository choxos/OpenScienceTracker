from django.core.management.base import BaseCommand
import pandas as pd
import os

class Command(BaseCommand):
    help = 'Explore CSV data to understand structure and potential issues'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping exploration.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🔍 Exploring CSV data structure...'))
        
        # Explore dental transparency database
        self.explore_dental_data()
        
        # Explore comprehensive journals
        self.explore_journal_data()
    
    def explore_dental_data(self):
        self.stdout.write('\n📄 DENTAL TRANSPARENCY DATABASE:')
        try:
            df = pd.read_csv('dental_ost_database.csv')
            self.stdout.write(f'📊 Shape: {df.shape}')
            self.stdout.write(f'📋 Columns: {list(df.columns)}')
            
            # Check for problematic fields
            self.stdout.write('\n🔍 FIELD LENGTH ANALYSIS:')
            
            # Check ISSN fields (should be ≤9 chars)
            issn_cols = ['journalIssn', 'journal_issn_electronic', 'journal_issn_print']
            for col in issn_cols:
                if col in df.columns:
                    max_len = df[col].astype(str).str.len().max()
                    long_values = df[col].astype(str).str.len() > 9
                    self.stdout.write(f'  {col}: max_length={max_len}, >9_chars={long_values.sum()}')
                    if long_values.sum() > 0:
                        samples = df[long_values][col].head(3).tolist()
                        self.stdout.write(f'    Examples: {samples}')
            
            # Check other varchar fields
            varchar_fields = ['pmid', 'pmcid', 'pub_type']
            for col in varchar_fields:
                if col in df.columns:
                    max_len = df[col].astype(str).str.len().max()
                    self.stdout.write(f'  {col}: max_length={max_len}')
            
            # Check datetime fields
            self.stdout.write('\n📅 DATETIME ANALYSIS:')
            date_cols = ['firstPublicationDate', 'assessment_date']
            for col in date_cols:
                if col in df.columns:
                    sample_values = df[col].dropna().head(3).tolist()
                    self.stdout.write(f'  {col}: samples={sample_values}')
            
            # Check boolean fields
            self.stdout.write('\n✅ BOOLEAN ANALYSIS:')
            bool_cols = ['is_coi_pred', 'is_fund_pred', 'is_open_data']
            for col in bool_cols:
                if col in df.columns:
                    unique_values = df[col].unique()
                    self.stdout.write(f'  {col}: unique_values={unique_values}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error exploring dental data: {e}'))
    
    def explore_journal_data(self):
        self.stdout.write('\n📚 COMPREHENSIVE JOURNALS DATABASE:')
        try:
            df = pd.read_csv('comprehensive_journal_database.csv')
            self.stdout.write(f'📊 Shape: {df.shape}')
            
            # Check for completely empty rows
            self.stdout.write('\n🕳️ EMPTY ROWS ANALYSIS:')
            key_fields = ['title_abbreviation', 'title_full', 'broad_subject_terms']
            
            for field in key_fields:
                if field in df.columns:
                    null_count = df[field].isnull().sum()
                    empty_count = (df[field] == '').sum()
                    self.stdout.write(f'  {field}: null={null_count}, empty={empty_count}')
            
            # Check rows where ALL key fields are empty
            mask_all_empty = True
            for field in key_fields:
                if field in df.columns:
                    mask_all_empty &= (df[field].isnull() | (df[field] == ''))
            
            empty_rows = mask_all_empty.sum()
            self.stdout.write(f'  📊 Completely empty rows: {empty_rows}')
            
            if empty_rows > 0:
                self.stdout.write('  📝 Sample empty row:')
                sample_empty = df[mask_all_empty].iloc[0].to_dict()
                for k, v in list(sample_empty.items())[:5]:
                    self.stdout.write(f'    {k}: {v}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error exploring journal data: {e}')) 