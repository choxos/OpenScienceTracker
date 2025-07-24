from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper


class Command(BaseCommand):
    help = 'Set all existing papers to open access (is_open_access=True)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of papers to update in each batch (default: 1000)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        # Count papers that need updating
        papers_to_update = Paper.objects.filter(is_open_access=False)
        total_count = papers_to_update.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('All papers are already marked as open access!')
            )
            return
        
        self.stdout.write(
            f'Found {total_count} papers that need to be marked as open access.'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No changes will be made.')
            )
            # Show sample of papers that would be updated
            sample_papers = papers_to_update[:10]
            for paper in sample_papers:
                self.stdout.write(f'  - {paper.pmid}: {paper.title[:60]}...')
            if total_count > 10:
                self.stdout.write(f'  ... and {total_count - 10} more papers')
            return
        
        # Confirm action
        confirm = input(f'Are you sure you want to mark {total_count} papers as open access? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Operation cancelled.')
            return
        
        # Update papers in batches
        updated_count = 0
        
        with transaction.atomic():
            # Use bulk_update for efficiency
            papers_list = list(papers_to_update)
            
            for i in range(0, len(papers_list), batch_size):
                batch = papers_list[i:i + batch_size]
                
                # Set is_open_access to True for this batch
                for paper in batch:
                    paper.is_open_access = True
                
                # Bulk update this batch
                Paper.objects.bulk_update(batch, ['is_open_access'], batch_size=batch_size)
                
                updated_count += len(batch)
                
                self.stdout.write(
                    f'Updated {updated_count}/{total_count} papers...',
                    ending='\r'
                )
        
        self.stdout.write('')  # New line
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} papers to open access!'
            )
        )
        
        # Verify the update
        remaining_non_oa = Paper.objects.filter(is_open_access=False).count()
        total_oa = Paper.objects.filter(is_open_access=True).count()
        
        self.stdout.write(
            f'Verification: {total_oa} papers marked as open access, '
            f'{remaining_non_oa} papers not open access.'
        )
        
        if remaining_non_oa == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ All papers are now marked as open access!')
            ) 