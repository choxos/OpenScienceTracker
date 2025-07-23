#!/usr/bin/env python3
"""
Deploy and import dental journals to Railway database
This script helps deploy the dental journal import to Railway
"""

import subprocess
import sys
import os

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Railway CLI found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Railway CLI not found")
            return False
    except FileNotFoundError:
        print("❌ Railway CLI not installed")
        return False

def check_required_files():
    """Check if required files exist"""
    required_files = [
        'dental_journals_ost.csv',
        'import_dental_journals_to_railway.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found")
    return True

def deploy_and_import():
    """Deploy files and run import on Railway"""
    print("🚀 Deploying dental journals to Railway...")
    
    # Check if we're in a Railway project
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not connected to a Railway project")
            print("Run 'railway login' and 'railway link' first")
            return False
    except Exception as e:
        print(f"❌ Error checking Railway status: {e}")
        return False
    
    print("✅ Connected to Railway project")
    
    # Create deployment directory
    print("📦 Preparing deployment files...")
    
    # Copy files that need to be on Railway
    files_to_upload = [
        'dental_journals_ost.csv',
        'import_dental_journals_to_railway.py',
        'manage.py',
        'requirements.txt'
    ]
    
    # Check file sizes
    csv_size = os.path.getsize('dental_journals_ost.csv') / (1024 * 1024)  # MB
    print(f"📄 Dental journals CSV size: {csv_size:.1f} MB")
    
    # Run the import
    print("\n🦷 Running dental journals import on Railway...")
    print("This may take a few minutes...")
    
    try:
        # Run the import script on Railway
        result = subprocess.run([
            'railway', 'run', 'python', 'import_dental_journals_to_railway.py'
        ], check=True, text=True)
        
        print("✅ Dental journals import completed successfully!")
        print("🌐 Check your database at: https://ost.xeradb.com/journals/")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Import failed: {e}")
        print("Check the Railway logs for more details:")
        print("railway logs")
        return False

def main():
    """Main deployment function"""
    print("🦷 Dental Journals Railway Deployment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_railway_cli():
        print("\n💡 To install Railway CLI:")
        print("npm install -g @railway/cli")
        print("or visit: https://docs.railway.app/cli/installation")
        return
    
    if not check_required_files():
        print("\n💡 Make sure you have:")
        print("- dental_journals_ost.csv (your dental journals data)")
        print("- import_dental_journals_to_railway.py (the import script)")
        return
    
    # Show what will happen
    print(f"\n📋 Deployment Plan:")
    print(f"   1. Check Railway connection")
    print(f"   2. Upload dental journals CSV ({os.path.getsize('dental_journals_ost.csv') / (1024*1024):.1f} MB)")
    print(f"   3. Run import script on Railway")
    print(f"   4. Update research fields")
    
    # Confirm deployment
    response = input(f"\n🚀 Ready to deploy dental journals to Railway? (y/N): ")
    if response.lower() != 'y':
        print("❌ Deployment cancelled")
        return
    
    # Run deployment
    success = deploy_and_import()
    
    if success:
        print(f"\n🎉 Success! Dental journals are now in your Railway database")
        print(f"🌐 Visit: https://ost.xeradb.com/fields/")
        print(f"📊 Check statistics: https://ost.xeradb.com/statistics/")
    else:
        print(f"\n❌ Deployment failed. Check the error messages above.")

if __name__ == "__main__":
    main() 