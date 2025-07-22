#!/usr/bin/env python3
"""
Generate secure SECRET_KEY for Django deployment
"""

import os
import sys

def generate_secret_key():
    """Generate a secure SECRET_KEY for Django"""
    try:
        # Method 1: Use Django's built-in generator (preferred)
        from django.core.management.utils import get_random_secret_key
        return get_random_secret_key()
    except ImportError:
        # Method 2: Fallback using Python's secrets module
        import secrets
        import string
        
        # Generate 50-character key with letters, digits, and safe symbols
        chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
        return ''.join(secrets.choice(chars) for _ in range(50))

if __name__ == "__main__":
    print("🔐 Django SECRET_KEY Generator")
    print("=" * 40)
    
    for i in range(3):
        key = generate_secret_key()
        print(f"Key {i+1}: {key}")
    
    print("\n📋 Usage for Railway deployment:")
    print(f"SECRET_KEY={generate_secret_key()}")
    
    print("\n⚠️  Important:")
    print("- Keep this key secret and secure")
    print("- Use different keys for different environments")
    print("- Never commit keys to version control")
    print("- Generate a new key if compromised") 