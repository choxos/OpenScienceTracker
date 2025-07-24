import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tracker.models import Paper
from collections import defaultdict

class Command(BaseCommand):
    help = 'Import NLM journal subject data and assign broad subject terms to papers based on ISSN matching'

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
            help='Number of papers to process per batch (default: 1000)'
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
            
            # Build ISSN-to-subject mapping
            issn_subject_map = self.build_issn_subject_mapping(nlm_df)
            
            # Match papers to subject terms
            self.match_papers_to_subjects(issn_subject_map)
            
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error processing CSV file: {str(e)}')

    def build_issn_subject_mapping(self, nlm_df):
        """Build a mapping from ISSN to broad subject terms"""
        self.stdout.write("🔗 Building ISSN-to-subject mapping...")
        
        issn_subject_map = {}
        subject_stats = defaultdict(int)
        
        for _, row in nlm_df.iterrows():
            broad_subject = row['broad_subject_term']
            if pd.isna(broad_subject):
                continue
                
            subject_stats[broad_subject] += 1
            
            # Collect all ISSNs for this journal
            issns = []
            
            if pd.notna(row['issn_electronic']) and row['issn_electronic']:
                issns.append(self.clean_issn(row['issn_electronic']))
            if pd.notna(row['issn_print']) and row['issn_print']:
                issns.append(self.clean_issn(row['issn_print']))
            if pd.notna(row['issn_linking']) and row['issn_linking']:
                issns.append(self.clean_issn(row['issn_linking']))
            
            # Map each ISSN to this broad subject
            for issn in issns:
                if issn:
                    if issn in issn_subject_map:
                        # Handle conflicts - keep the first one or use a priority system
                        if issn_subject_map[issn] != broad_subject:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠️ ISSN conflict: {issn} maps to both '{issn_subject_map[issn]}' and '{broad_subject}'"
                                )
                            )
                    else:
                        issn_subject_map[issn] = broad_subject
        
        # Print subject statistics
        self.stdout.write(f"📊 Subject term statistics:")
        for subject, count in sorted(subject_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            self.stdout.write(f"   {subject}: {count} journals")
        
        self.stdout.write(f"🔗 Created ISSN mapping for {len(issn_subject_map):,} ISSNs across {len(subject_stats)} subject terms")
        
        return issn_subject_map

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
        
        return None

    def match_papers_to_subjects(self, issn_subject_map):
        """Match papers to broad subject terms based on ISSN"""
        self.stdout.write("🔍 Matching papers to subject terms...")
        
        total_papers = Paper.objects.count()
        matched_count = 0
        updated_count = 0
        
        # Process papers in batches
        batch_num = 0
        total_batches = (total_papers + self.batch_size - 1) // self.batch_size
        
        for batch_start in range(0, total_papers, self.batch_size):
            batch_num += 1
            batch_end = min(batch_start + self.batch_size, total_papers)
            
            self.stdout.write(f"🔄 Processing batch {batch_num}/{total_batches} (papers {batch_start+1}-{batch_end})")
            
            papers = Paper.objects.all()[batch_start:batch_end]
            
            with transaction.atomic():
                for paper in papers:
                    subject = self.find_subject_for_paper(paper, issn_subject_map)
                    
                    if subject:
                        matched_count += 1
                        
                        if not self.dry_run:
                            if paper.broad_subject_term != subject:
                                paper.broad_subject_term = subject
                                paper.save(update_fields=['broad_subject_term'])
                                updated_count += 1
                        else:
                            # In dry run, assume all matches would be updates
                            if paper.broad_subject_term != subject:
                                updated_count += 1
        
        # Print summary
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"🔍 DRY RUN RESULTS:\n"
                    f"   📊 Total papers: {total_papers:,}\n"
                    f"   🎯 Papers that would be matched: {matched_count:,} ({(matched_count/total_papers)*100:.1f}%)\n"
                    f"   🔄 Papers that would be updated: {updated_count:,}\n"
                    f"   📋 Use --dry-run=False to apply changes"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Subject matching complete!\n"
                    f"   📊 Total papers: {total_papers:,}\n"
                    f"   🎯 Papers matched: {matched_count:,} ({(matched_count/total_papers)*100:.1f}%)\n"
                    f"   🔄 Papers updated: {updated_count:,}"
                )
            )
        
        # Show subject distribution if not dry run
        if not self.dry_run and matched_count > 0:
            self.show_subject_distribution()

    def find_subject_for_paper(self, paper, issn_subject_map):
        """Find the broad subject term for a paper based on its journal ISSN"""
        # Try to match using the paper's journal ISSN
        if paper.journal_issn:
            clean_issn = self.clean_issn(paper.journal_issn)
            if clean_issn and clean_issn in issn_subject_map:
                return issn_subject_map[clean_issn]
        
        # If no direct match, try to extract ISSN from other sources
        # (This could be expanded to include more sophisticated matching)
        
        return None

    def show_subject_distribution(self):
        """Show the distribution of papers across subject terms"""
        self.stdout.write("📈 Subject term distribution in papers:")
        
        subject_counts = Paper.objects.filter(
            broad_subject_term__isnull=False
        ).values('broad_subject_term').annotate(
            count=models.Count('id')
        ).order_by('-count')[:20]
        
        for item in subject_counts:
            subject = item['broad_subject_term']
            count = item['count']
            self.stdout.write(f"   {subject}: {count:,} papers")
        
        total_with_subjects = Paper.objects.filter(broad_subject_term__isnull=False).count()
        total_papers = Paper.objects.count()
        
        self.stdout.write(f"📊 Total papers with subject terms: {total_with_subjects:,} / {total_papers:,} ({(total_with_subjects/total_papers)*100:.1f}%)")

    def create_subject_summary_report(self):
        """Create a summary report of subject matching results"""
        if self.dry_run:
            return
        
        report_file = "subject_matching_report.csv"
        
        # Get subject statistics
        subject_stats = Paper.objects.filter(
            broad_subject_term__isnull=False
        ).values('broad_subject_term').annotate(
            paper_count=models.Count('id'),
            transparency_processed_count=models.Count('id', filter=models.Q(transparency_processed=True)),
            open_access_count=models.Count('id', filter=models.Q(is_open_access=True)),
            avg_transparency_score=models.Avg('transparency_score')
        ).order_by('-paper_count')
        
        # Convert to DataFrame and save
        df = pd.DataFrame(list(subject_stats))
        df['transparency_processed_pct'] = (df['transparency_processed_count'] / df['paper_count'] * 100).round(1)
        df['open_access_pct'] = (df['open_access_count'] / df['paper_count'] * 100).round(1)
        df['avg_transparency_score'] = df['avg_transparency_score'].round(2)
        
        df.to_csv(report_file, index=False)
        self.stdout.write(f"📄 Subject summary report saved to: {report_file}")

# Add missing import for models
from django.db import models 