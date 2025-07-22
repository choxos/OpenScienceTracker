#!/usr/bin/env python3
"""
Railway Deployment Helper Script
Automates the complete deployment process for OpenScienceTracker
"""

import subprocess
import sys
import os
import time

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {description}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    print("🚀 Railway Deployment Helper for OpenScienceTracker")
    print("=" * 60)
    
    # Step 1: Check if Railway CLI is installed
    print("\n📋 Pre-deployment Checklist:")
    
    try:
        subprocess.run(["railway", "--version"], check=True, capture_output=True)
        print("✅ Railway CLI is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI not found. Please install it first:")
        print("   npm install -g @railway/cli")
        return
    
    # Step 2: Check Railway login status
    try:
        result = subprocess.run(["railway", "whoami"], check=True, capture_output=True, text=True)
        print(f"✅ Logged in to Railway as: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("❌ Not logged in to Railway. Please run:")
        print("   railway login")
        return
    
    # Step 3: Deploy to Railway
    print("\n🚀 Starting Railway Deployment:")
    
    commands = [
        ("git add .", "Adding files to git"),
        ("git commit -m 'Add OSF import command and deployment improvements'", "Committing changes"),
        ("git push origin main", "Pushing to GitHub"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"⚠️  Warning: {description} failed, but continuing...")
    
    print("\n📋 Next Steps to Complete Deployment:")
    print("=" * 50)
    print("1. 🌐 Go to Railway.app and check your deployment status")
    print("2. 🔧 Verify environment variables are set:")
    print("   - SECRET_KEY")
    print("   - DEBUG=False") 
    print("   - ALLOWED_HOSTS=*.railway.app,.railway.app")
    print("3. 🗄️  PostgreSQL database should be auto-configured")
    print("")
    print("4. 📊 Once deployed, import data using ONE of these methods:")
    print("")
    print("   Method A - Import from OSF (Recommended):")
    print("   railway run python manage.py import_from_osf --dataset both")
    print("")
    print("   Method B - Test import (smaller dataset):")
    print("   railway run python manage.py import_from_osf --dataset dental --max-records 1000")
    print("")
    print("5. 👤 Create superuser:")
    print("   Go to Railway dashboard → Services → [Your service] → 'Command' tab")
    print("   Run: python manage.py createsuperuser")
    print("")
    print("6. 🔄 Run migrations if needed:")
    print("   railway run python manage.py migrate")
    print("")
    print("🎉 Your app will be available at: https://[your-project].railway.app")

if __name__ == "__main__":
    main() 