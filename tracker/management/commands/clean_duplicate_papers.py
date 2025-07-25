from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper
from collections import defaultdict

class Command(BaseCommand):
    help = 'Clean up duplicate papers in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes',
        )
        parser.add_argument(
            '--field',
            type=str,
            choices=['pmid', 'pmcid', 'doi', 'epmc_id', 'all'],
            default='all',
            help='Which field to check for duplicates (default: all)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        field = options['field']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made"))
        
        if field == 'all':
            fields_to_check = ['pmid', 'pmcid', 'doi', 'epmc_id']
        else:
            fields_to_check = [field]
        
        total_duplicates_found = 0
        total_duplicates_removed = 0
        
        for field_name in fields_to_check:
            self.stdout.write(f"\n📋 Checking for duplicates in field: {field_name}")
            duplicates_found, duplicates_removed = self.clean_duplicates_by_field(field_name)
            total_duplicates_found += duplicates_found
            total_duplicates_removed += duplicates_removed
        
        # Summary
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 DRY RUN SUMMARY:\n"
                    f"   📊 Total duplicate groups found: {total_duplicates_found}\n"
                    f"   🗑️ Papers that would be removed: {total_duplicates_removed}\n"
                    f"   ▶️ Run without --dry-run to apply changes"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ CLEANUP COMPLETE:\n"
                    f"   📊 Total duplicate groups found: {total_duplicates_found}\n"
                    f"   🗑️ Papers removed: {total_duplicates_removed}\n"
                    f"   💾 Database cleaned successfully"
                )
            )

    def clean_duplicates_by_field(self, field_name):
        """Clean duplicates for a specific field"""
        duplicates_found = 0
        duplicates_removed = 0
        
        # Find all non-null values for this field with their counts
        field_values = Paper.objects.filter(
            **{f'{field_name}__isnull': False}
        ).exclude(
            **{field_name: ''}
        ).values_list(field_name, flat=True)
        
        # Group by field value to find duplicates
        value_counts = defaultdict(int)
        for value in field_values:
            value_counts[value] += 1
        
        # Process duplicates
        for field_value, count in value_counts.items():
            if count > 1:
                duplicates_found += 1
                self.stdout.write(f"   🔍 Found {count} papers with {field_name}='{field_value}'")
                
                # Get all papers with this field value
                duplicate_papers = Paper.objects.filter(
                    **{field_name: field_value}
                ).order_by('-updated_at', '-created_at')  # Keep the most recently updated
                
                # Keep the first (most recent), remove the rest
                papers_to_keep = duplicate_papers.first()
                papers_to_remove = duplicate_papers[1:]
                
                if papers_to_remove:
                    for paper in papers_to_remove:
                        self.stdout.write(
                            f"      ➜ {'[DRY RUN] Would remove' if self.dry_run else 'Removing'}: "
                            f"ID {paper.pk} - '{paper.title[:50]}...'"
                        )
                        
                        if not self.dry_run:
                            # Merge any unique data before deletion
                            self.merge_paper_data(papers_to_keep, paper)
                            paper.delete()
                            duplicates_removed += 1
                        else:
                            duplicates_removed += 1
                    
                    if not self.dry_run:
                        papers_to_keep.save()  # Save any merged data
        
        self.stdout.write(f"   📊 {field_name}: {duplicates_found} duplicate groups, {duplicates_removed} papers {'would be ' if self.dry_run else ''}removed")
        return duplicates_found, duplicates_removed

    def merge_paper_data(self, keep_paper, remove_paper):
        """Merge useful data from paper being removed into the paper being kept"""
        # List of fields to potentially merge (prefer non-empty values)
        merge_fields = [
            'title', 'author_string', 'journal_title', 'journal_issn',
            'pub_year', 'pmid', 'pmcid', 'doi', 'source',
            'transparency_score', 'assessment_tool'
        ]
        
        updated = False
        for field in merge_fields:
            keep_value = getattr(keep_paper, field)
            remove_value = getattr(remove_paper, field)
            
            # If keep_paper field is empty but remove_paper has data, use remove_paper's data
            if (not keep_value or keep_value == '') and remove_value and remove_value != '':
                setattr(keep_paper, field, remove_value)
                updated = True
                self.stdout.write(f"         📝 Merged {field}: '{remove_value}'")
        
        # Merge transparency indicators (prefer True values)
        transparency_fields = [
            'is_open_data', 'is_open_code', 'is_coi_pred', 'is_fund_pred', 
            'is_register_pred', 'is_open_access', 'transparency_processed'
        ]
        
        for field in transparency_fields:
            keep_value = getattr(keep_paper, field)
            remove_value = getattr(remove_paper, field)
            
            # If remove_paper has True and keep_paper has False/None, update to True
            if remove_value and not keep_value:
                setattr(keep_paper, field, remove_value)
                updated = True
                self.stdout.write(f"         ✅ Updated {field}: {remove_value}")
        
        return updated 