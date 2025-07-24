from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Paper, Journal
from django.db.models import Q

class Command(BaseCommand):
    help = 'Match papers to journals based on journal name and ISSN'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be matched without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of papers to process per batch (default: 100)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('🔗 Starting journal matching process...'))
        
        # Build journal mapping for efficient lookup
        self.stdout.write("📚 Building journal mapping...")
        journal_map = self.build_journal_mapping()
        self.stdout.write(f"📚 Built journal mapping with {len(journal_map)} entries")
        
        # Get papers that need journal matching
        papers_to_match = Paper.objects.filter(
            Q(journal__title_abbreviation='Unknown Journal') |
            Q(journal__isnull=True)
        )
        
        total_papers = papers_to_match.count()
        self.stdout.write(f"📄 Found {total_papers} papers to match")
        
        if total_papers == 0:
            self.stdout.write(self.style.SUCCESS('✅ No papers need journal matching'))
            return
        
        # Process papers in batches
        matched_count = 0
        no_match_count = 0
        batch_count = 0
        
        for i in range(0, total_papers, batch_size):
            batch_count += 1
            batch_papers = papers_to_match[i:i + batch_size]
            
            self.stdout.write(f"🔄 Processing batch {batch_count} ({len(batch_papers)} papers)...")
            
            batch_matched, batch_no_match = self.process_batch(
                batch_papers, journal_map, dry_run
            )
            
            matched_count += batch_matched
            no_match_count += batch_no_match
        
        # Report results
        self.stdout.write(self.style.SUCCESS('✅ Journal matching completed!'))
        self.stdout.write(f'📊 Results:')
        self.stdout.write(f'   ✅ Papers matched: {matched_count}')
        self.stdout.write(f'   ❌ Papers with no match: {no_match_count}')
        self.stdout.write(f'   📈 Match rate: {(matched_count/total_papers*100):.1f}%')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  This was a dry run - no changes were made'))

    def build_journal_mapping(self):
        """Build efficient journal lookup mapping"""
        journal_map = {}
        
        # Get all journals from database
        journals = Journal.objects.all().values(
            'id', 'nlm_id', 'title_abbreviation', 'title_full', 
            'issn_print', 'issn_electronic', 'issn_linking'
        )
        
        for journal in journals:
            j_id = journal['id']
            
            # Map by NLM ID (most reliable)
            if journal['nlm_id']:
                journal_map[f"nlm:{journal['nlm_id']}"] = j_id
            
            # Map by title abbreviation (case-insensitive)
            if journal['title_abbreviation']:
                key = f"title:{journal['title_abbreviation'].lower().strip()}"
                journal_map[key] = j_id
            
            # Map by title full (case-insensitive)
            if journal['title_full']:
                key = f"title:{journal['title_full'].lower().strip()}"
                journal_map[key] = j_id
            
            # Map by all ISSN variants
            for issn_field in ['issn_print', 'issn_electronic', 'issn_linking']:
                issn = journal[issn_field]
                if issn:
                    journal_map[f"issn:{issn.strip()}"] = j_id
        
        return journal_map
    
    def process_batch(self, papers, journal_map, dry_run):
        """Process a batch of papers for journal matching"""
        matched_count = 0
        no_match_count = 0
        updates = []
        
        for paper in papers:
            journal_id = self.find_journal_id(paper, journal_map)
            
            if journal_id and journal_id != paper.journal_id:
                matched_journal = Journal.objects.get(id=journal_id)
                
                # Show what would be matched
                self.stdout.write(
                    f"  📝 {paper.pmid}: '{paper.journal_title}' → "
                    f"'{matched_journal.title_full}'"
                )
                
                if not dry_run:
                    paper.journal_id = journal_id
                    updates.append(paper)
                
                matched_count += 1
            else:
                self.stdout.write(
                    f"  ❌ {paper.pmid}: No match for '{paper.journal_title}' "
                    f"(ISSN: {paper.journal_issn or 'None'})"
                )
                no_match_count += 1
        
        # Bulk update if not dry run
        if not dry_run and updates:
            with transaction.atomic():
                Paper.objects.bulk_update(updates, ['journal'])
        
        return matched_count, no_match_count
    
    def find_journal_id(self, paper, journal_map):
        """Find the correct journal ID for a paper"""
        
        # Try journal title first (most common case)
        journal_title = paper.journal_title
        if journal_title:
            # Try exact match
            key = f"title:{journal_title.lower().strip()}"
            if key in journal_map:
                return journal_map[key]
            
            # Try partial matching for common variations
            journal_title_clean = self.clean_journal_title(journal_title)
            if journal_title_clean:
                key = f"title:{journal_title_clean}"
                if key in journal_map:
                    return journal_map[key]
        
        # Try ISSN matching
        journal_issn = paper.journal_issn
        if journal_issn:
            # Handle multiple ISSNs separated by semicolons or commas
            issn_separators = [';', ',', '|']
            issns = [journal_issn]  # Start with the whole string
            
            for separator in issn_separators:
                if separator in journal_issn:
                    issns = [issn.strip() for issn in journal_issn.split(separator) if issn.strip()]
                    break
            
            for issn in issns:
                issn_clean = self.clean_issn(issn)
                if issn_clean:
                    key = f"issn:{issn_clean}"
                    if key in journal_map:
                        return journal_map[key]
        
        # No match found
        return None
    
    def clean_journal_title(self, title):
        """Clean journal title for better matching"""
        if not title:
            return ""
        
        # Remove common suffixes/prefixes that might cause mismatches
        title = title.lower().strip()
        
        # Remove trailing periods
        title = title.rstrip('.')
        
        # Remove common prefixes
        prefixes_to_remove = ['the ', 'journal of ', 'international ']
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):]
        
        # Remove common suffixes
        suffixes_to_remove = [' journal', ' magazine', ' review']
        for suffix in suffixes_to_remove:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
        
        return title.strip()
    
    def clean_issn(self, issn):
        """Clean and validate ISSN"""
        if not issn:
            return ""
        
        # Remove whitespace and convert to string
        issn = str(issn).strip()
        
        # Remove common prefixes
        if issn.lower().startswith('issn:'):
            issn = issn[5:].strip()
        
        # Basic ISSN format validation (XXXX-XXXX)
        if len(issn) in [8, 9]:
            # Remove any existing hyphens and reformat
            digits = issn.replace('-', '')
            if len(digits) == 8 and digits.isdigit():
                return f"{digits[:4]}-{digits[4:]}"
        
        return issn  # Return as-is if not standard format 