#!/usr/bin/env python3
"""
Simple script to monitor medical transparency import progress
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper, Journal

def monitor_progress():
    """Monitor import progress"""
    print(f"📊 Import Progress Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Get current counts
    total_papers = Paper.objects.count()
    dental_papers = Paper.objects.filter(broad_subject_category__in=['Dentistry', 'Orthodontics']).count()
    medical_papers = total_papers - dental_papers
    total_journals = Journal.objects.count()
    
    print(f"📈 Current Database Statistics:")
    print(f"   - Total papers: {total_papers:,}")
    print(f"   - Medical papers: {medical_papers:,}")
    print(f"   - Dental papers: {dental_papers:,}")
    print(f"   - Total journals: {total_journals:,}")
    
    # Target information
    target_medical = 2704359  # Based on our file analysis
    current_progress = (medical_papers / target_medical) * 100 if target_medical > 0 else 0
    
    print(f"\n🎯 Import Progress:")
    print(f"   - Target medical papers: {target_medical:,}")
    print(f"   - Progress: {current_progress:.2f}%")
    print(f"   - Remaining: {target_medical - medical_papers:,}")
    
    if medical_papers > 0 and medical_papers < target_medical:
        # Estimate time remaining (very rough)
        print(f"\n⏱️  Import Status: IN PROGRESS")
        print(f"   - Processing large dataset...")
        print(f"   - Estimated total time: 9-22 hours")
    elif medical_papers >= target_medical:
        print(f"\n✅ Import Status: COMPLETED!")
    else:
        print(f"\n🔄 Import Status: STARTING...")
    
    # Recent papers by category
    print(f"\n🏷️  Top Subject Categories:")
    from django.db.models import Count
    categories = Paper.objects.exclude(broad_subject_category__isnull=True).values('broad_subject_category').annotate(count=Count('id')).order_by('-count')[:8]
    
    for cat in categories:
        print(f"   - {cat['broad_subject_category']}: {cat['count']:,} papers")


if __name__ == "__main__":
    monitor_progress() 