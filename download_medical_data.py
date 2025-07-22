#!/usr/bin/env python3
"""
Download medical transparency data from OSF repository
"""

import os
import sys
import urllib.request
from urllib.parse import urlparse

def download_medical_data():
    """Download medical transparency data from OSF"""
    print("📥 Downloading Medical Transparency Data from OSF")
    print("=" * 50)
    
    # OSF direct download URL
    osf_url = "https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499"
    target_file = "papers/medicaltransparency_opendata.csv"
    
    # Create papers directory if it doesn't exist
    os.makedirs("papers", exist_ok=True)
    
    # Check if file already exists
    if os.path.exists(target_file):
        file_size = os.path.getsize(target_file) / (1024**3)  # GB
        print(f"✅ File already exists: {target_file}")
        print(f"📁 Size: {file_size:.2f} GB")
        
        response = input("🤔 Re-download? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("📊 Using existing file")
            return target_file
    
    print(f"📡 Source: {osf_url}")
    print(f"💾 Target: {target_file}")
    print(f"⚠️  Warning: This is a large file (2.5+ GB)")
    print(f"🕐 Download may take several minutes depending on connection")
    
    # Confirm download
    response = input("🚀 Start download? (Y/n): ").strip().lower()
    if response in ['n', 'no']:
        print("❌ Download cancelled")
        return None
    
    try:
        print(f"\n📥 Starting download...")
        
        # Download with progress indication
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                downloaded = block_num * block_size / (1024**2)  # MB
                total_mb = total_size / (1024**2)  # MB
                print(f"\r📊 Progress: {percent:3d}% ({downloaded:.1f}/{total_mb:.1f} MB)", end='', flush=True)
        
        urllib.request.urlretrieve(osf_url, target_file, progress_hook)
        print()  # New line after progress
        
        # Verify download
        if os.path.exists(target_file):
            file_size = os.path.getsize(target_file) / (1024**3)  # GB
            print(f"✅ Download completed successfully!")
            print(f"📁 File: {target_file}")
            print(f"📏 Size: {file_size:.2f} GB")
            
            # Quick validation
            try:
                with open(target_file, 'r', encoding='latin-1') as f:
                    header = f.readline().strip()
                print(f"📋 Header preview: {header[:100]}...")
                return target_file
            except Exception as e:
                print(f"⚠️  Warning: Could not read file header: {e}")
                return target_file
        else:
            print(f"❌ Download failed: File not found")
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        print(f"💡 Try downloading manually from: {osf_url}")
        return None

def main():
    """Main function"""
    print("🔬 Open Science Tracker - Medical Data Download")
    print(f"📊 Data Source: OSF Repository")
    print(f"🏥 Content: Medical transparency assessments (~2.7M papers)")
    print(f"🔬 Tool: rtransparent package")
    print()
    
    # Download the data
    result = download_medical_data()
    
    if result:
        print(f"\n🎉 Ready for import!")
        print(f"📝 Next steps:")
        print(f"   1. Test data: python test_medical_import.py")
        print(f"   2. Import data: python import_medical_transparency_data.py")
        print(f"   3. Monitor progress: python monitor_import_progress.py")
    else:
        print(f"\n💡 Manual download instructions:")
        print(f"   1. Visit: https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499")
        print(f"   2. Download file to: papers/medicaltransparency_opendata.csv")
        print(f"   3. Run: python test_medical_import.py")

if __name__ == "__main__":
    main() 