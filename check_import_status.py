#!/usr/bin/env python
"""
Diagnostic script to check medical papers import status
Run this to understand why 0 papers were imported
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from tracker.models import Paper
from django.db.models import Count, Q

def main():
    print("🔍 Open Science Tracker - Import Status Diagnosis")
    print("=" * 50)
    
    # Basic statistics
    total_papers = Paper.objects.count()
    print(f"📊 Total papers in database: {total_papers:,}")
    
    # Check papers by assessment tool
    rtransparent_papers = Paper.objects.filter(assessment_tool='rtransparent').count()
    other_papers = total_papers - rtransparent_papers
    
    print(f"🔬 Papers with rtransparent assessment: {rtransparent_papers:,}")
    print(f"📋 Papers with other assessments: {other_papers:,}")
    
    if rtransparent_papers > 0:
        percentage = (rtransparent_papers / total_papers) * 100
        print(f"📈 Percentage rtransparent: {percentage:.1f}%")
    
    print("\n" + "=" * 50)
    
    # Assessment tool breakdown
    print("🛠️  Assessment Tool Breakdown:")
    assessment_stats = Paper.objects.values('assessment_tool').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for stat in assessment_stats:
        tool = stat['assessment_tool'] or 'Unknown'
        count = stat['count']
        print(f"   {tool}: {count:,} papers")
    
    print("\n" + "=" * 50)
    
    # Check recent papers
    print("📅 Recent Papers (last 10):")
    recent_papers = Paper.objects.order_by('-created_at')[:10]
    
    for paper in recent_papers:
        created = paper.created_at.strftime('%Y-%m-%d %H:%M')
        assessment = paper.assessment_tool or 'Unknown'
        print(f"   {paper.epmc_id} | {assessment} | {created}")
    
    print("\n" + "=" * 50)
    
    # Year distribution
    print("📊 Papers by Publication Year (recent):")
    year_stats = Paper.objects.filter(
        pub_year__gte=2020
    ).values('pub_year').annotate(
        count=Count('id')
    ).order_by('-pub_year')[:5]
    
    for stat in year_stats:
        year = stat['pub_year']
        count = stat['count']
        print(f"   {year}: {count:,} papers")
    
    print("\n" + "=" * 50)
    
    # Recommendations
    print("💡 Next Steps Recommendations:")
    
    if rtransparent_papers == 0:
        print("   ✅ No rtransparent papers found - import will add new data")
        print("   🔧 Recommendation: Re-run import without --update flag")
        print("   📝 Command: python manage.py import_medical_papers_bulk [file.csv]")
    
    elif rtransparent_papers > 0 and rtransparent_papers == total_papers:
        print("   ✅ All papers are from rtransparent assessment")
        print("   🔧 Recommendation: Import was likely successful previously")
        print("   📝 Your data is already in the database!")
    
    elif rtransparent_papers > 0 and rtransparent_papers < total_papers:
        print("   ✅ Mixed assessment tools detected")
        print("   🔧 Recommendation: Use --update-existing to refresh rtransparent papers")
        print("   📝 Command: python manage.py import_medical_papers_bulk [file.csv] --update-existing")
    
    else:
        print("   ⚠️  Unexpected state - manual investigation needed")
    
    print("\n" + "=" * 50)
    
    # File size check
    rtransparent_file = Path("rtransparent_csvs/medicaltransparency_opendata.csv")
    if rtransparent_file.exists():
        size_mb = rtransparent_file.stat().st_size / (1024 * 1024)
        print(f"📁 Import file size: {size_mb:.1f} MB")
        print(f"📍 Import file location: {rtransparent_file}")
    else:
        print("❌ Import file not found at expected location")
        print("📍 Expected: rtransparent_csvs/medicaltransparency_opendata.csv")
    
    print("\n🎯 Import Status: COMPLETE - Data verification recommended")

if __name__ == "__main__":
    main() 