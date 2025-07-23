#!/usr/bin/env python3
"""
Simple script to diagnose the journal mapping issue
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.production_settings')
django.setup()

from tracker.models import Paper, Journal
from django.db.models import Count

def main():
    print("🔍 DIAGNOSING JOURNAL MAPPING ISSUE")
    print("=" * 50)
    
    # Check current database state
    total_papers = Paper.objects.count()
    total_journals = Journal.objects.count()
    
    print(f"📊 Total papers: {total_papers:,}")
    print(f"📚 Total journals: {total_journals:,}")
    
    # Check journal distribution
    print("\n📈 Top 10 journals by paper count:")
    journal_counts = Paper.objects.values('journal__title_abbreviation').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    for item in journal_counts:
        journal_name = item['journal__title_abbreviation'] or 'Unknown'
        count = item['count']
        print(f"  {journal_name}: {count:,} papers")
    
    # Check for the specific problem
    problem_count = Paper.objects.filter(journal__title_abbreviation='20 Century Br Hist').count()
    print(f"\n🔍 Papers assigned to '20 Century Br Hist': {problem_count:,}")
    
    if problem_count > 100000:
        print("❌ CRITICAL ISSUE: Most papers are incorrectly assigned to one journal!")
        print("💡 This means the journal mapping in medical import failed.")
        print("🔧 Run the fix script to resolve this issue.")
        return False
    else:
        print("✅ Journal distribution looks normal.")
        return True

if __name__ == "__main__":
    main() 