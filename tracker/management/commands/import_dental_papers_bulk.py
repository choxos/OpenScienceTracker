from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal
import pandas as pd
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Bulk import dental transparency papers (respects Django defaults)'

    def handle(self, *args, **options):
        # Only run in Railway environment
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🦷 Bulk importing dental transparency papers...'))
        
        # Check if already imported to avoid duplicates
        existing_papers = Paper.objects.filter(journal_title__icontains='dental').count()
        if existing_papers > 1000:
            self.stdout.write(self.style.WARNING(f'✅ Dental papers already imported ({existing_papers:,} found). Skipping.'))
            return
        
        try:
            # Load dental transparency database
            df = pd.read_csv('dental_ost_database.csv')
            self.stdout.write(f"📄 Processing {len(df):,} dental transparency records")
            
            # Clean data
            df = df.fillna('')
            df = df.where(pd.notnull(df), None)
            
            # Convert to model instances in batches
            papers = []
            batch_size = 1000
            
            for idx, row in df.iterrows():
                # Create Paper instance - Django will apply model defaults
                paper = Paper(
                    pmid=self.clean_field(row.get('pmid')),
                    pmcid=self.clean_field(row.get('pmcid')),
                    doi=self.clean_field(row.get('doi')),
                    title=self.clean_field(row.get('title')) or 'Unknown Title',
                    author_string=self.clean_field(row.get('authorString')),
                    journal_title=self.clean_field(row.get('journalTitle')) or 'Unknown Journal',
                    journal_issn=self.clean_issn(row.get('journalIssn')),
                    pub_year=self.clean_year(row.get('year_firstpub')) or 2020,
                    first_publication_date=self.clean_date(row.get('firstPublicationDate')),
                    year_first_pub=self.clean_year(row.get('year_firstpub')),
                    month_first_pub=self.clean_number(row.get('month_firstpub')),
                    journal_volume=self.clean_field(row.get('journalVolume')),
                    page_info=self.clean_field(row.get('pageInfo')),
                    issue=self.clean_field(row.get('issue')),
                    pub_type=self.clean_field(row.get('type')),
                    jif2020=self.clean_float(row.get('jif2020')),
                    scimago_publisher=self.clean_field(row.get('publisher')),
                    
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
                    
                    # Journal reference (default to 1 if no match)
                    journal_id=1,
                )
                papers.append(paper)
                
                # Batch insert every 1000 records
                if len(papers) >= batch_size:
                    with transaction.atomic():
                        Paper.objects.bulk_create(papers, ignore_conflicts=True)
                    self.stdout.write(f'  ✅ Imported batch of {len(papers)} papers...')
                    papers = []
            
            # Insert remaining papers
            if papers:
                with transaction.atomic():
                    Paper.objects.bulk_create(papers, ignore_conflicts=True)
                self.stdout.write(f'  ✅ Imported final batch of {len(papers)} papers')
            
            # Report results
            total_papers = Paper.objects.count()
            dental_papers = Paper.objects.filter(journal_title__icontains='dental').count()
            
            self.stdout.write(self.style.SUCCESS('✅ Bulk import completed!'))
            self.stdout.write(f'📊 Total papers: {total_papers:,}')
            self.stdout.write(f'🦷 Dental papers: {dental_papers:,}')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('❌ File dental_ost_database.csv not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Full error: {traceback.format_exc()}'))
    
    def clean_field(self, value):
        """Clean field value"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        return str(value).strip()
    
    def clean_boolean(self, value):
        """Clean boolean value"""
        if pd.isna(value) or value == "nan" or value == "":
            return False
        return str(value).upper() in ['TRUE', '1', 'YES', 'T']
    
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
    
    def clean_issn(self, value):
        """Clean ISSN field (max 9 chars)"""
        if pd.isna(value) or value == "nan" or value == "":
            return ""
        issn = str(value).strip()
        # Truncate to 9 characters if longer
        return issn[:9] if len(issn) > 9 else issn
    
    def clean_date_tz(self, value):
        """Clean date field with timezone awareness"""
        if pd.isna(value) or value == "nan" or value == "":
            return None
        try:
            from django.utils import timezone as tz
            dt = pd.to_datetime(value, errors='coerce')
            if dt is not None and not pd.isna(dt):
                # Make timezone-aware if naive
                if dt.tzinfo is None:
                    return tz.make_aware(dt, tz.get_current_timezone())
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