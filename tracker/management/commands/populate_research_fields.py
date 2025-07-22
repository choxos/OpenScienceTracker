from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from tracker.models import Paper, Journal, ResearchField


class Command(BaseCommand):
    help = 'Populate ResearchField model with all unique subject categories from papers and journals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-stats',
            action='store_true',
            help='Update statistics for existing fields',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting ResearchField population...'))
        
        # Get all unique subject categories from papers
        paper_categories = Paper.objects.exclude(
            broad_subject_category__isnull=True
        ).exclude(
            broad_subject_category=''
        ).values_list('broad_subject_category', flat=True).distinct()
        
        self.stdout.write(f"📊 Found {len(paper_categories)} unique subject categories in papers")
        
        # Get all unique subject terms from journals
        journal_terms = set()
        journals_with_terms = Journal.objects.exclude(
            broad_subject_terms__isnull=True
        ).exclude(broad_subject_terms='')
        
        for journal in journals_with_terms:
            if journal.broad_subject_terms:
                terms = journal.broad_subject_terms.split(';')
                for term in terms:
                    term = term.strip()
                    if term:
                        journal_terms.add(term)
        
        self.stdout.write(f"📚 Found {len(journal_terms)} unique subject terms in journals")
        
        # Combine both sources
        all_categories = set(paper_categories) | journal_terms
        self.stdout.write(f"🔗 Total unique categories to process: {len(all_categories)}")
        
        created_count = 0
        updated_count = 0
        
        for category in sorted(all_categories):
            if not category.strip():
                continue
                
            # Create or get the research field
            field, created = ResearchField.objects.get_or_create(
                name=category.strip(),
                defaults={
                    'description': f'Research field for {category.strip()}',
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"  ✅ Created: {category}")
            elif options['update_stats']:
                updated_count += 1
            
            # Update statistics
            self.update_field_statistics(field)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ ResearchField population completed!\n'
                f'   📝 Created: {created_count} new fields\n'
                f'   🔄 Updated: {updated_count} existing fields\n'
                f'   📊 Total fields: {ResearchField.objects.count()}'
            )
        )

    def update_field_statistics(self, field):
        """Update statistics for a research field"""
        # Count papers with this exact subject category
        papers_exact = Paper.objects.filter(broad_subject_category=field.name)
        
        # Count papers from journals that contain this subject term
        papers_from_journals = Paper.objects.filter(
            journal__broad_subject_terms__icontains=field.name
        )
        
        # Count journals that contain this subject term
        journals_count = Journal.objects.filter(
            broad_subject_terms__icontains=field.name
        ).count()
        
        # Use the larger count (exact matches or journal-based)
        total_papers = max(papers_exact.count(), papers_from_journals.count())
        
        # Calculate average transparency score
        if total_papers > 0:
            avg_transparency = papers_from_journals.aggregate(
                avg=Avg('transparency_score')
            )['avg'] or 0.0
        else:
            avg_transparency = 0.0
        
        # Update the field
        field.total_papers = total_papers
        field.total_journals = journals_count
        field.avg_transparency_score = round(avg_transparency, 2)
        field.save() 