#!/usr/bin/env python3
"""
Quick script to clear cache and warm it up
Run this after updating the homepage
"""

import os
import sys
import django

# Add project root to Python path
sys.path.append('/var/www/ost')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

from django.core.cache import cache
from tracker.cache_utils import warm_cache, invalidate_stats_cache

print("🔄 Clearing cache...")
cache.clear()

print("🔄 Invalidating statistics cache...")
invalidate_stats_cache()

print("🔥 Warming up cache with fresh data...")
warm_cache()

print("✅ Cache refresh complete!") 