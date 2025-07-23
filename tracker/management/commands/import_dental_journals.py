from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Journal, ResearchField
import pandas as pd
import numpy as np
from datetime import datetime


class Command(BaseCommand):
    help = 'Import dental journals from dental_journals_ost.csv to Railway database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making database changes',
        )

    def handle(self, *args, **options):
        # Only run in Railway environment
        import os
        if not os.environ.get('RAILWAY_ENVIRONMENT'):
            self.stdout.write(self.style.WARNING('⚠️  Not in Railway environment. Skipping dental journals import.'))
            return
            
        self.stdout.write(self.style.SUCCESS('🦷 Importing Dental Journals to Railway Database'))
        self.stdout.write('=' * 60)
        
        # Check if dental journals are already imported
        existing_dental_count = Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count()
        if existing_dental_count > 100:  # Assume if we have >100 dental journals, import was already done
            self.stdout.write(self.style.WARNING(f'✅ Dental journals already imported ({existing_dental_count:,} found). Skipping import.'))
            return
        
        # Check if CSV file exists
        csv_file = 'dental_journals_ost.csv'
        try:
            # Load the CSV file
            self.stdout.write(f"📄 Loading {csv_file}...")
            df = pd.read_csv(csv_file, encoding='utf-8')
            self.stdout.write(f"   ✅ Loaded {len(df):,} dental journal records")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error loading CSV: {e}"))
            return

        # Show sample data
        self.stdout.write(f"\n📊 Sample columns: {list(df.columns)[:5]}...")
        
        # Check database connection
        try:
            current_journal_count = Journal.objects.count()
            self.stdout.write(f"\n📚 Current journals in database: {current_journal_count:,}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection error: {e}"))
            return

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No changes will be made"))
            return

        # Import journals
        self.stdout.write(f"\n🔄 Processing dental journals...")
        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            with transaction.atomic():
                for idx, row in df.iterrows():
                    if idx % 100 == 0:
                        self.stdout.write(f"   Processing {idx:,}/{len(df):,} journals...")

                    try:
                        # Extract and clean data
                        nlm_id = self.clean_text_field(row.get('nlm_id'))
                        if not nlm_id or nlm_id == "":
                            error_count += 1
                            continue

                        title_abbreviation = self.clean_text_field(row.get('title_abbreviation')) or 'Unknown'
                        title_full = self.clean_text_field(row.get('title_full'))

                        # Create or update journal
                        journal, created = Journal.objects.get_or_create(
                            nlm_id=nlm_id,
                            defaults={
                                'title_abbreviation': title_abbreviation,
                                'title_full': title_full,
                                'authors': self.clean_text_field(row.get('authors')),
                                'publication_start_year': self.clean_year_field(row.get('publication_start_year')),
                                'publication_end_year': self.clean_year_field(row.get('publication_end_year')),
                                'frequency': self.clean_text_field(row.get('frequency')),
                                'country': self.clean_text_field(row.get('country')),
                                'publisher': self.clean_text_field(row.get('publisher')),
                                'language': self.clean_text_field(row.get('language')),
                                'issn_electronic': self.clean_text_field(row.get('issn_electronic')),
                                'issn_print': self.clean_text_field(row.get('issn_print')),
                                'issn_linking': self.clean_text_field(row.get('issn_linking')),
                                'lccn': self.clean_text_field(row.get('lccn')),
                                'electronic_links': self.clean_text_field(row.get('electronic_links')),
                                'indexing_status': self.clean_text_field(row.get('indexing_status')),
                                'mesh_terms': self.clean_text_field(row.get('mesh_terms')),
                                'publication_types': self.clean_text_field(row.get('publication_types')),
                                'notes': self.clean_text_field(row.get('notes')),
                                'broad_subject_terms': self.clean_text_field(row.get('broad_subject_terms')),
                                'subject_term_count': self.clean_number_field(row.get('subject_term_count')) or 1,
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            # Update existing journal with any missing data
                            updated = False

                            # Update fields that might be missing
                            if not journal.title_full and title_full:
                                journal.title_full = title_full
                                updated = True

                            if not journal.country and self.clean_text_field(row.get('country')):
                                journal.country = self.clean_text_field(row.get('country'))
                                updated = True

                            if not journal.publisher and self.clean_text_field(row.get('publisher')):
                                journal.publisher = self.clean_text_field(row.get('publisher'))
                                updated = True

                            if not journal.broad_subject_terms and self.clean_text_field(row.get('broad_subject_terms')):
                                journal.broad_subject_terms = self.clean_text_field(row.get('broad_subject_terms'))
                                updated = True

                            if updated:
                                journal.save()
                                updated_count += 1

                    except Exception as e:
                        self.stdout.write(f"   ⚠️  Error processing row {idx}: {e}")
                        error_count += 1
                        continue

            self.stdout.write(self.style.SUCCESS(f"\n✅ Dental journals import completed!"))
            self.stdout.write(f"📊 Import Statistics:")
            self.stdout.write(f"   - Total processed: {len(df):,}")
            self.stdout.write(f"   - New journals created: {created_count:,}")
            self.stdout.write(f"   - Existing journals updated: {updated_count:,}")
            self.stdout.write(f"   - Errors: {error_count:,}")

            # Updated database statistics
            final_count = Journal.objects.count()
            self.stdout.write(f"\n📈 Database Statistics:")
            self.stdout.write(f"   - Previous journal count: {current_journal_count:,}")
            self.stdout.write(f"   - Current journal count: {final_count:,}")
            self.stdout.write(f"   - Net increase: {final_count - current_journal_count:,}")

            # Check dental journals specifically
            dental_journals = Journal.objects.filter(
                broad_subject_terms__icontains='Dentistry'
            ).count()
            self.stdout.write(f"   - Total dental journals: {dental_journals:,}")

            # Update research fields
            self.update_research_fields()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Critical error during import: {e}"))

    def clean_text_field(self, value):
        """Clean text field for database storage"""
        if pd.isna(value) or value == "" or value == "nan":
            return ""
        return str(value).strip()

    def clean_year_field(self, value):
        """Clean year field for database storage"""
        if pd.isna(value) or value == "" or value == "nan":
            return None
        try:
            year = int(float(value))
            if 1800 <= year <= 2030:  # Reasonable year range
                return year
        except (ValueError, TypeError):
            pass
        return None

    def clean_number_field(self, value):
        """Clean numeric field for database storage"""
        if pd.isna(value) or value == "" or value == "nan":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def update_research_fields(self):
        """Update research fields after importing dental journals"""
        self.stdout.write(f"\n🔄 Updating research fields...")

        # Ensure 'Dentistry' field exists and has correct statistics
        dentistry_field, created = ResearchField.objects.get_or_create(
            name='Dentistry',
            defaults={'description': 'Dental research and oral health'}
        )

        # Update statistics
        dental_journals_count = Journal.objects.filter(
            broad_subject_terms__icontains='Dentistry'
        ).count()

        dentistry_field.total_journals = dental_journals_count
        dentistry_field.save()

        self.stdout.write(f"   ✅ Updated Dentistry field with {dental_journals_count:,} journals") 