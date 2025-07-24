#!/usr/bin/env python3
"""
Manual Data Processing Script for Open Science Tracker
Author: Ahmad Sofi-Mahmudi

This script allows manual processing of EPMC and transparency data files
on the VPS when automatic monitoring is not sufficient.
"""

import os
import sys
import argparse
from pathlib import Path
import django

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from django.core.management import call_command
from tracker.models import Paper, Journal

def show_status():
    """Show current database status"""
    paper_count = Paper.objects.count()
    journal_count = Journal.objects.count()
    transparency_processed = Paper.objects.filter(transparency_processed=True).count()
    
    print(f"\n=== Current Database Status ===")
    print(f"Total Papers: {paper_count:,}")
    print(f"Total Journals: {journal_count:,}")
    print(f"Papers with Transparency Data: {transparency_processed:,}")
    print(f"Transparency Coverage: {(transparency_processed/paper_count*100):.1f}%" if paper_count > 0 else "0%")
    
    # Check file directories
    epmc_dir = '/home/xeradb/epmc_monthly_data'
    transparency_dir = '/home/xeradb/transparency_results'
    
    epmc_files = len([f for f in os.listdir(epmc_dir) if f.endswith('.csv')]) if os.path.exists(epmc_dir) else 0
    transparency_files = len([f for f in os.listdir(transparency_dir) if f.endswith('.csv')]) if os.path.exists(transparency_dir) else 0
    
    print(f"\nFiles waiting to be processed:")
    print(f"EPMC files: {epmc_files}")
    print(f"Transparency files: {transparency_files}")

def main():
    parser = argparse.ArgumentParser(description='Manually process OST data files')
    parser.add_argument('--epmc', action='store_true', help='Process all EPMC files')
    parser.add_argument('--transparency', action='store_true', help='Process all transparency files')
    parser.add_argument('--all', action='store_true', help='Process all files')
    parser.add_argument('--file', type=str, help='Process specific file')
    parser.add_argument('--status', action='store_true', help='Show database status')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without executing')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be processed")
    
    if args.all or args.epmc:
        print("Processing EPMC files...")
        if not args.dry_run:
            call_command('process_epmc_files')
        else:
            print("Would call: python manage.py process_epmc_files")
    
    if args.all or args.transparency:
        print("Processing transparency files...")
        if not args.dry_run:
            call_command('process_transparency_files')
        else:
            print("Would call: python manage.py process_transparency_files")
    
    if args.file:
        if 'epmc' in args.file.lower():
            print(f"Processing EPMC file: {args.file}")
            if not args.dry_run:
                call_command('process_epmc_files', file=args.file)
            else:
                print(f"Would call: python manage.py process_epmc_files --file {args.file}")
        elif 'transparency' in args.file.lower():
            print(f"Processing transparency file: {args.file}")
            if not args.dry_run:
                call_command('process_transparency_files', file=args.file)
            else:
                print(f"Would call: python manage.py process_transparency_files --file {args.file}")
        else:
            print("ERROR: Cannot determine file type from filename")
            print("File should contain 'epmc' or 'transparency' in the name")
            return
    
    if not any([args.all, args.epmc, args.transparency, args.file, args.status]):
        parser.print_help()

if __name__ == "__main__":
    main() 