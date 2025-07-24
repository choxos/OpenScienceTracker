import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Avg, Q
from tracker.models import Paper, Journal, ResearchField
from collections import defaultdict

class Command(BaseCommand):
    help = 'Populate ResearchField model from NLM broad subject terms assigned to papers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update statistics for existing research fields',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting ResearchField population from NLM data...'))
        
        # Get all unique broad subject terms from papers
        subject_terms = Paper.objects.filter(
            broad_subject_term__isnull=False
        ).exclude(
            broad_subject_term=''
        ).values_list('broad_subject_term', flat=True).distinct().order_by('broad_subject_term')
        
        self.stdout.write(f"📊 Found {len(subject_terms)} unique broad subject terms in papers")
        
        # Also get subject terms from the consolidated NLM journals data
        nlm_file = 'nlm_journals_consolidated.csv'
        additional_terms = set()
        
        try:
            df = pd.read_csv(nlm_file)
            for subject_term in df['broad_subject_term'].dropna().unique():
                if subject_term and subject_term.strip():
                    additional_terms.add(subject_term.strip())
            
            self.stdout.write(f"📚 Found {len(additional_terms)} additional terms from NLM catalog")
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f"⚠️  NLM file {nlm_file} not found, using only paper data"))
        
        # Combine both sources
        all_terms = set(subject_terms) | additional_terms
        self.stdout.write(f"🔗 Total unique subject terms to process: {len(all_terms)}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
            for term in sorted(all_terms):
                papers_count = Paper.objects.filter(broad_subject_term=term).count()
                self.stdout.write(f"  📝 Would create/update: {term} ({papers_count} papers)")
            return
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for term in sorted(all_terms):
                if not term or not term.strip():
                    continue
                    
                # Calculate statistics for this term
                papers_in_term = Paper.objects.filter(broad_subject_term=term)
                papers_count = papers_in_term.count()
                
                # Get journals for this term from our NLM data
                try:
                    df = pd.read_csv(nlm_file)
                    journals_count = len(df[df['broad_subject_term'] == term])
                except:
                    # Fallback: count unique journals from papers
                    journals_count = papers_in_term.values('journal').distinct().count()
                
                # Calculate transparency statistics
                avg_transparency = papers_in_term.aggregate(
                    avg=Avg('transparency_score')
                )['avg'] or 0.0
                
                # Calculate individual indicator averages (as percentages)
                if papers_count > 0:
                    avg_data_sharing = (papers_in_term.filter(is_open_data=True).count() / papers_count) * 100
                    avg_code_sharing = (papers_in_term.filter(is_open_code=True).count() / papers_count) * 100
                    avg_coi_disclosure = (papers_in_term.filter(is_coi_pred=True).count() / papers_count) * 100
                    avg_funding_disclosure = (papers_in_term.filter(is_fund_pred=True).count() / papers_count) * 100
                    avg_protocol_registration = (papers_in_term.filter(is_register_pred=True).count() / papers_count) * 100
                    avg_open_access = (papers_in_term.filter(is_open_access=True).count() / papers_count) * 100
                else:
                    avg_data_sharing = 0.0
                    avg_code_sharing = 0.0
                    avg_coi_disclosure = 0.0
                    avg_funding_disclosure = 0.0
                    avg_protocol_registration = 0.0
                    avg_open_access = 0.0
                
                # Create or update the research field
                field, created = ResearchField.objects.get_or_create(
                    name=term.strip(),
                    defaults={
                        'description': f'Research field covering {term.strip()} as classified by NLM',
                        'total_papers': papers_count,
                        'total_journals': journals_count,
                        'avg_transparency_score': round(avg_transparency, 2),
                        'avg_data_sharing': round(avg_data_sharing, 1),
                        'avg_code_sharing': round(avg_code_sharing, 1),
                        'avg_coi_disclosure': round(avg_coi_disclosure, 1),
                        'avg_funding_disclosure': round(avg_funding_disclosure, 1),
                        'avg_protocol_registration': round(avg_protocol_registration, 1),
                        'avg_open_access': round(avg_open_access, 1),
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"  ✅ Created: {term} ({papers_count} papers, {journals_count} journals)")
                elif options['update_existing']:
                    # Update existing field statistics
                    field.total_papers = papers_count
                    field.total_journals = journals_count
                    field.avg_transparency_score = round(avg_transparency, 2)
                    field.avg_data_sharing = round(avg_data_sharing, 1)
                    field.avg_code_sharing = round(avg_code_sharing, 1)
                    field.avg_coi_disclosure = round(avg_coi_disclosure, 1)
                    field.avg_funding_disclosure = round(avg_funding_disclosure, 1)
                    field.avg_protocol_registration = round(avg_protocol_registration, 1)
                    field.avg_open_access = round(avg_open_access, 1)
                    field.save()
                    updated_count += 1
                    self.stdout.write(f"  🔄 Updated: {term} ({papers_count} papers, {journals_count} journals)")
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ ResearchField population completed!\n'
                f'   📝 Created: {created_count} new fields\n'
                f'   🔄 Updated: {updated_count} existing fields\n'
                f'   📊 Total fields in database: {ResearchField.objects.count()}\n'
                f'   🏆 Top 5 fields by paper count:'
            )
        )
        
        # Show top fields
        top_fields = ResearchField.objects.filter(total_papers__gt=0).order_by('-total_papers')[:5]
        for i, field in enumerate(top_fields, 1):
            self.stdout.write(f"      {i}. {field.name}: {field.total_papers} papers") 