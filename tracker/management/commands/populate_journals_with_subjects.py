import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tracker.models import Paper, Journal
from collections import defaultdict

class Command(BaseCommand):
    help = 'Populate Journal table with broad subject terms from NLM data and link Papers to Journals'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            default='nlm_journals_consolidated.csv',
            help='Path to the consolidated NLM journals CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch (default: 1000)'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options['batch_size']
        csv_file = options['csv_file']
        
        self.stdout.write(f"📚 Loading NLM journal data from: {csv_file}")
        
        try:
            # Load the consolidated NLM journal data
            nlm_df = pd.read_csv(csv_file)
            self.stdout.write(f"📄 Loaded {len(nlm_df):,} journal records from NLM data")
            
            # Step 1: Populate Journal table with NLM data
            journals_created, journals_updated = self.populate_journal_table(nlm_df)
            
            # Step 2: Link Papers to Journals via ISSN matching
            papers_linked = self.link_papers_to_journals()
            
            # Step 3: Show summary
            self.show_summary(journals_created, journals_updated, papers_linked)
            
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error processing CSV file: {str(e)}')

    def populate_journal_table(self, nlm_df):
        """Create/update Journal records with NLM data including broad subject terms"""
        self.stdout.write("📖 Populating Journal table with NLM data...")
        
        journals_created = 0
        journals_updated = 0
        
        for _, row in nlm_df.iterrows():
            if pd.isna(row.get('title_full')) or not str(row['title_full']).strip():
                continue
                
            journal_data = {
                'title_full': str(row['title_full']).strip(),
                'title_abbreviation': str(row.get('title_abbreviation', row['title_full'])).strip()[:100],
                'nlm_id': str(row.get('nlm_id', '')).strip() or None,
                'broad_subject_terms': str(row.get('broad_subject_term', '')).strip() or None,
                'country': str(row.get('country', '')).strip()[:100] or None,
                'publisher': str(row.get('publisher', '')).strip()[:500] or None,
                'publication_start_year': self.safe_int(row.get('publication_start_year')),
                'publication_end_year': self.safe_int(row.get('publication_end_year')),
                'issn_electronic': self.clean_issn(row.get('issn_electronic')),
                'issn_print': self.clean_issn(row.get('issn_print')),
                'issn_linking': self.clean_issn(row.get('issn_linking')),
                'indexing_status': str(row.get('indexing_status', '')).strip()[:200] or None,
                'language': str(row.get('language', '')).strip()[:100] or None,
            }
            
            if not self.dry_run:
                # Try to find existing journal by title or ISSN
                existing_journal = self.find_existing_journal(journal_data)
                
                if existing_journal:
                    # Update existing journal
                    updated = False
                    for field, value in journal_data.items():
                        if field != 'title_full' and getattr(existing_journal, field) != value:
                            setattr(existing_journal, field, value)
                            updated = True
                    
                    if updated:
                        existing_journal.save()
                        journals_updated += 1
                else:
                    # Create new journal
                    Journal.objects.create(**journal_data)
                    journals_created += 1
            else:
                # Dry run logic
                existing_journal = self.find_existing_journal(journal_data)
                if existing_journal:
                    journals_updated += 1
                else:
                    journals_created += 1
        
        self.stdout.write(f"📖 Journal population complete: {journals_created} created, {journals_updated} updated")
        return journals_created, journals_updated

    def find_existing_journal(self, journal_data):
        """Find existing journal by title or ISSN"""
        # Try by title first
        try:
            return Journal.objects.get(title_full=journal_data['title_full'])
        except Journal.DoesNotExist:
            pass
        
        # Try by ISSN
        for issn_field in ['issn_electronic', 'issn_print', 'issn_linking']:
            issn = journal_data.get(issn_field)
            if issn:
                existing = Journal.objects.filter(
                    models.Q(issn_electronic=issn) |
                    models.Q(issn_print=issn) |
                    models.Q(issn_linking=issn)
                ).first()
                if existing:
                    return existing
        
        return None

    def link_papers_to_journals(self):
        """Link Papers to Journals via ISSN matching"""
        self.stdout.write("🔗 Linking Papers to Journals via ISSN...")
        
        total_papers = Paper.objects.count()
        papers_linked = 0
        
        # Process papers in batches
        batch_num = 0
        total_batches = (total_papers + self.batch_size - 1) // self.batch_size
        
        for batch_start in range(0, total_papers, self.batch_size):
            batch_num += 1
            batch_end = min(batch_start + self.batch_size, total_papers)
            
            self.stdout.write(f"🔄 Processing batch {batch_num}/{total_batches} (papers {batch_start+1}-{batch_end})")
            
            papers = Paper.objects.filter(journal__isnull=True)[batch_start:batch_end]
            
            with transaction.atomic():
                for paper in papers:
                    journal = self.find_journal_for_paper(paper)
                    
                    if journal and not self.dry_run:
                        paper.journal = journal
                        paper.save(update_fields=['journal'])
                        papers_linked += 1
                    elif journal and self.dry_run:
                        papers_linked += 1
        
        self.stdout.write(f"🔗 Paper linking complete: {papers_linked} papers linked to journals")
        return papers_linked

    def find_journal_for_paper(self, paper):
        """Find the appropriate journal for a paper based on ISSN or title"""
        # Try by paper's journal_issn
        if paper.journal_issn:
            clean_issn = self.clean_issn(paper.journal_issn)
            if clean_issn:
                journal = Journal.objects.filter(
                    models.Q(issn_electronic=clean_issn) |
                    models.Q(issn_print=clean_issn) |
                    models.Q(issn_linking=clean_issn)
                ).first()
                if journal:
                    return journal
        
        # Try by journal title
        if paper.journal_title:
            journal = Journal.objects.filter(title_full__iexact=paper.journal_title.strip()).first()
            if journal:
                return journal
        
        return None

    def clean_issn(self, issn):
        """Clean and normalize ISSN format"""
        if not issn or pd.isna(issn):
            return None
        
        issn = str(issn).strip().upper()
        
        # Remove any extra characters and format as XXXX-XXXX
        issn = ''.join(c for c in issn if c.isdigit() or c.upper() == 'X')
        
        if len(issn) == 8:
            return f"{issn[:4]}-{issn[4:]}"
        elif len(issn) == 9 and issn[4] == '-':
            return issn
        
        return issn[:20] if len(issn) <= 20 else None  # Truncate if too long

    def safe_int(self, value):
        """Safely convert to integer"""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def show_summary(self, journals_created, journals_updated, papers_linked):
        """Show final summary of the operation"""
        total_journals = Journal.objects.count() if not self.dry_run else "N/A (dry run)"
        total_papers = Paper.objects.count() if not self.dry_run else "N/A (dry run)"
        papers_with_journals = Paper.objects.filter(journal__isnull=False).count() if not self.dry_run else "N/A (dry run)"
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"🔍 DRY RUN RESULTS:\n"
                    f"   📖 Journals that would be created: {journals_created:,}\n"
                    f"   📖 Journals that would be updated: {journals_updated:,}\n"
                    f"   🔗 Papers that would be linked: {papers_linked:,}\n"
                    f"   📋 Use without --dry-run to apply changes"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Journal and Paper linking complete!\n"
                    f"   📖 Total journals in database: {total_journals:,}\n"
                    f"   🔗 Papers linked to journals: {papers_with_journals:,} / {total_papers:,}\n"
                    f"   📊 Coverage: {(papers_with_journals/total_papers*100):.1f}%" if total_papers > 0 else ""
                )
            )
            
            # Show subject distribution
            self.show_subject_distribution()

    def show_subject_distribution(self):
        """Show the distribution of papers across subject terms via journal relationships"""
        self.stdout.write("📈 Subject term distribution (via Journal relationships):")
        
        # Get subject distribution through journal relationships
        from django.db.models import Count
        
        subject_counts = Journal.objects.filter(
            broad_subject_terms__isnull=False,
            papers__isnull=False
        ).values('broad_subject_terms').annotate(
            paper_count=Count('papers', distinct=True)
        ).order_by('-paper_count')[:20]
        
        for item in subject_counts:
            subject = item['broad_subject_terms']
            count = item['paper_count']
            self.stdout.write(f"   {subject}: {count:,} papers")
        
        total_papers_with_subjects = Paper.objects.filter(
            journal__broad_subject_terms__isnull=False
        ).count()
        total_papers = Paper.objects.count()
        
        self.stdout.write(f"📊 Total papers with subject terms (via journals): {total_papers_with_subjects:,} / {total_papers:,} ({(total_papers_with_subjects/total_papers)*100:.1f}%)")

# Add missing imports
from django.db import models 