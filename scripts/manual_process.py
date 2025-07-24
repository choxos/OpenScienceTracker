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

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("  Open Science Tracker - Manual Data Processing")
    print("  Author: Ahmad Sofi-Mahmudi")
    print("=" * 60)

def check_directories():
    """Check if data directories exist"""
    epmc_dir = '/home/ost/epmc_monthly_data'
    transparency_dir = '/home/ost/transparency_results'
    
    issues = []
    
    if not os.path.exists(epmc_dir):
        issues.append(f"EPMC directory missing: {epmc_dir}")
    else:
        epmc_files = [f for f in os.listdir(epmc_dir) if f.endswith('.csv')]
        print(f"✓ EPMC directory: {len(epmc_files)} CSV files found")
    
    if not os.path.exists(transparency_dir):
        issues.append(f"Transparency directory missing: {transparency_dir}")
    else:
        transparency_files = [f for f in os.listdir(transparency_dir) if f.endswith('.csv')]
        print(f"✓ Transparency directory: {len(transparency_files)} CSV files found")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print()
    
    return len(issues) == 0

def process_epmc_files(dry_run=False):
    """Process EPMC files"""
    print("\n📊 Processing EPMC files...")
    try:
        if dry_run:
            call_command('process_epmc_files', dry_run=True)
        else:
            call_command('process_epmc_files')
        print("✅ EPMC processing completed")
    except Exception as e:
        print(f"❌ EPMC processing failed: {str(e)}")
        return False
    return True

def process_transparency_files(dry_run=False):
    """Process transparency files"""
    print("\n🔍 Processing transparency files...")
    try:
        if dry_run:
            call_command('process_transparency_files', dry_run=True)
        else:
            call_command('process_transparency_files')
        print("✅ Transparency processing completed")
    except Exception as e:
        print(f"❌ Transparency processing failed: {str(e)}")
        return False
    return True

def process_specific_file(file_path):
    """Process a specific file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    filename = os.path.basename(file_path)
    print(f"\n📁 Processing specific file: {filename}")
    
    try:
        if 'epmc' in filename.lower():
            call_command('process_epmc_files', file=file_path)
            print(f"✅ EPMC file processed: {filename}")
        elif 'transparency' in filename.lower():
            call_command('process_transparency_files', file=file_path)
            print(f"✅ Transparency file processed: {filename}")
        else:
            print(f"❌ Cannot determine file type from filename: {filename}")
            print("   File should contain 'epmc' or 'transparency' in the name")
            return False
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        return False
    
    return True

def show_status():
    """Show current system status"""
    print("\n📈 Current System Status:")
    try:
        from tracker.models import Paper, Journal
        
        total_papers = Paper.objects.count()
        total_journals = Journal.objects.count()
        processed_papers = Paper.objects.filter(transparency_processed=True).count()
        
        print(f"   Papers in database: {total_papers:,}")
        print(f"   Journals in database: {total_journals:,}")
        print(f"   Papers with transparency data: {processed_papers:,}")
        
        if total_papers > 0:
            processing_rate = (processed_papers / total_papers) * 100
            print(f"   Transparency processing rate: {processing_rate:.1f}%")
        
        # Check recent files
        epmc_dir = '/home/ost/epmc_monthly_data'
        transparency_dir = '/home/ost/transparency_results'
        
        if os.path.exists(epmc_dir):
            unprocessed_epmc = len([f for f in os.listdir(epmc_dir) 
                                  if f.endswith('.csv') and not f.startswith('.')])
            print(f"   Unprocessed EPMC files: {unprocessed_epmc}")
        
        if os.path.exists(transparency_dir):
            unprocessed_transparency = len([f for f in os.listdir(transparency_dir) 
                                          if f.endswith('.csv') and not f.startswith('.')])
            print(f"   Unprocessed transparency files: {unprocessed_transparency}")
        
    except Exception as e:
        print(f"   ❌ Error getting status: {str(e)}")

def main():
    parser = argparse.ArgumentParser(
        description='Manually process Open Science Tracker data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    # Process all unprocessed files
  %(prog)s --epmc                   # Process only EPMC files  
  %(prog)s --transparency           # Process only transparency files
  %(prog)s --file data.csv          # Process specific file
  %(prog)s --status                 # Show current status
  %(prog)s --dry-run --all          # Show what would be processed
        """
    )
    
    parser.add_argument('--epmc', action='store_true', 
                       help='Process all unprocessed EPMC files')
    parser.add_argument('--transparency', action='store_true', 
                       help='Process all unprocessed transparency files')
    parser.add_argument('--all', action='store_true', 
                       help='Process all unprocessed files (EPMC + transparency)')
    parser.add_argument('--file', type=str, 
                       help='Process specific file (full path)')
    parser.add_argument('--status', action='store_true',
                       help='Show current system status')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without making changes')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Show status if requested
    if args.status:
        show_status()
        if not any([args.epmc, args.transparency, args.all, args.file]):
            return
    
    # Check directories
    if not check_directories():
        print("⚠️  Please fix directory issues before processing")
        sys.exit(1)
    
    success = True
    
    # Process specific file
    if args.file:
        success = process_specific_file(args.file)
    
    # Process all files
    elif args.all:
        success &= process_epmc_files(args.dry_run)
        success &= process_transparency_files(args.dry_run)
    
    # Process EPMC files only
    elif args.epmc:
        success = process_epmc_files(args.dry_run)
    
    # Process transparency files only
    elif args.transparency:
        success = process_transparency_files(args.dry_run)
    
    # No action specified, show help
    else:
        parser.print_help()
        print("\n💡 Tip: Start with --status to see current system state")
        print("       Use --dry-run to test before actual processing")
        return
    
    # Final status
    if success:
        print("\n🎉 Processing completed successfully!")
        if not args.dry_run:
            show_status()
    else:
        print("\n❌ Some processing failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 