#!/usr/bin/env python3
"""
Quick test script for rtransparent data import
Tests with small batches to verify import functionality before full import
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run test imports with different configurations"""
    
    # Check if CSV file exists
    csv_file = "rtransparent_csvs/medicaltransparency_opendata.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print("Please ensure the file is in the correct location.")
        return False
    
    print("🔬 Testing rtransparent import functionality")
    print(f"📁 CSV file: {csv_file}")
    print(f"📊 File size: {os.path.getsize(csv_file) / (1024*1024*1024):.2f} GB")
    print()
    
    # Test 1: Dry run with 10 records
    print("🧪 Test 1: Dry run (10 records)")
    result = run_command([
        "python", "manage.py", "import_rtransparent_bulk", csv_file,
        "--limit", "10", "--dry-run", "--create-journals"
    ])
    if not result:
        return False
    
    # Test 2: Small import with 50 records
    print("\n🧪 Test 2: Small import (50 records)")
    result = run_command([
        "python", "manage.py", "import_rtransparent_bulk", csv_file,
        "--limit", "50", "--create-journals"
    ])
    if not result:
        return False
    
    # Test 3: Medium import with 500 records
    print("\n🧪 Test 3: Medium import (500 records)")
    result = run_command([
        "python", "manage.py", "import_rtransparent_bulk", csv_file,
        "--limit", "500", "--create-journals", "--update-existing"
    ])
    if not result:
        return False
    
    # Check database status
    print("\n📊 Checking database status...")
    result = run_command([
        "python", "manage.py", "shell", "-c",
        "from tracker.models import Paper; print(f'Total papers in database: {Paper.objects.count():,}')"
    ])
    
    print("\n✅ All tests completed successfully!")
    print("\n🚀 Ready for full import. Run:")
    print(f"python manage.py import_rtransparent_bulk {csv_file} --create-journals")
    
    return True

def run_command(cmd_list):
    """Run a command and show output"""
    try:
        print(f"Running: {' '.join(cmd_list)}")
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Success")
            if result.stdout:
                print("Output:", result.stdout[-200:])  # Show last 200 chars
        else:
            print("❌ Failed")
            print("Error:", result.stderr)
            return False
            
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

if __name__ == "__main__":
    # Change to project directory if script is run from elsewhere
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if manage.py exists
    if not os.path.exists("manage.py"):
        print("❌ manage.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1) 