"""
Caching utilities for the Open Science Tracker
Provides high-level caching functions for expensive database operations
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Avg, Q
from functools import wraps
import hashlib
import json

def make_cache_key(*args, **kwargs):
    """Generate a consistent cache key from arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {}
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    hash_object = hashlib.md5(key_string.encode())
    return f"ost_{hash_object.hexdigest()}"

def cached_query(timeout=None, key_prefix='query'):
    """
    Decorator for caching expensive database queries
    
    Usage:
    @cached_query(timeout=300, key_prefix='home_stats')
    def get_home_statistics():
        return expensive_query()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}_{make_cache_key(func.__name__, *args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_timeout = timeout or getattr(settings, 'CACHE_TIMEOUTS', {}).get('default', 900)
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator

@cached_query(timeout=900, key_prefix='home_stats')  # 15 minutes
def get_home_page_statistics(year_filter='2000'):
    """Get cached statistics for home page"""
    from .models import Paper
    
    papers_queryset = Paper.objects.all()
    if year_filter == '2000':
        papers_queryset = papers_queryset.filter(pub_year__gte=2000)
    
    stats = papers_queryset.aggregate(
        total_papers=Count('id'),
        avg_transparency_score=Avg('transparency_score'),
        open_data_count=Count('id', filter=Q(is_open_data=True)),
        open_code_count=Count('id', filter=Q(is_open_code=True)),
        coi_count=Count('id', filter=Q(is_coi_pred=True)),
        funding_count=Count('id', filter=Q(is_fund_pred=True)),
        registration_count=Count('id', filter=Q(is_register_pred=True)),
        open_access_count=Count('id', filter=Q(is_open_access=True))
    )
    
    # Calculate percentages
    total_papers = max(stats['total_papers'], 1)
    stats.update({
        'open_data_pct': round((stats['open_data_count'] / total_papers) * 100, 1),
        'open_code_pct': round((stats['open_code_count'] / total_papers) * 100, 1),
        'coi_pct': round((stats['coi_count'] / total_papers) * 100, 1),
        'funding_pct': round((stats['funding_count'] / total_papers) * 100, 1),
        'registration_pct': round((stats['registration_count'] / total_papers) * 100, 1),
        'open_access_pct': round((stats['open_access_count'] / total_papers) * 100, 1),
    })
    
    return stats

@cached_query(timeout=1800, key_prefix='field_stats')  # 30 minutes
def get_field_statistics():
    """Get cached statistics for research fields"""
    from .models import ResearchField
    
    # Convert QuerySet to list for caching
    fields = ResearchField.objects.all().order_by('-total_papers', 'name')
    return list(fields)

@cached_query(timeout=1800, key_prefix='journal_stats')  # 30 minutes  
def get_journal_statistics():
    """Get cached journal statistics"""
    from .models import Journal
    
    # Convert QuerySet to list for caching
    journals = Journal.objects.annotate(
        paper_count=Count('papers'),
        avg_transparency=Avg('papers__transparency_score')
    ).filter(paper_count__gt=0).order_by('-paper_count')
    return list(journals)

@cached_query(timeout=3600, key_prefix='transparency_trends')  # 1 hour
def get_transparency_trends():
    """Get transparency trends over time"""
    from .models import Paper
    
    # Get yearly transparency trends
    trends = Paper.objects.filter(
        pub_year__gte=2000,
        pub_year__lte=2023
    ).values('pub_year').annotate(
        total_papers=Count('id'),
        avg_transparency=Avg('transparency_score'),
        open_data_pct=Count('id', filter=Q(is_open_data=True)) * 100.0 / Count('id'),
        open_code_pct=Count('id', filter=Q(is_open_code=True)) * 100.0 / Count('id'),
        coi_pct=Count('id', filter=Q(is_coi_pred=True)) * 100.0 / Count('id'),
    ).order_by('pub_year')
    
    return list(trends)

@cached_query(timeout=600, key_prefix='search_counts')  # 10 minutes
def get_search_filter_counts():
    """Get counts for search filters"""
    from .models import Paper, Journal
    
    return {
        'total_papers': Paper.objects.count(),
        'total_journals': Journal.objects.count(),
        'years_available': list(
            Paper.objects.values_list('pub_year', flat=True)
            .distinct().order_by('-pub_year')[:20]
        ),
        'top_subjects': list(
            Paper.objects.values_list('broad_subject_term', flat=True)
            .exclude(broad_subject_term__isnull=True)
            .exclude(broad_subject_term='')
            .distinct()[:50]
        ),
    }

def invalidate_cache_pattern(pattern):
    """Invalidate cache keys matching a pattern"""
    # Note: This requires Redis backend for pattern-based deletion
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f"*{pattern}*")
    else:
        # Fallback: clear entire cache
        cache.clear()

def invalidate_stats_cache():
    """Invalidate all statistics caches when data changes"""
    patterns = ['home_stats', 'field_stats', 'journal_stats', 'transparency_trends', 'search_counts']
    for pattern in patterns:
        invalidate_cache_pattern(pattern)

# Cache warming functions (run these periodically)
def warm_cache():
    """Warm up the cache with commonly accessed data"""
    # Warm home page stats for both year filters
    get_home_page_statistics('2000')
    get_home_page_statistics('all')
    
    # Warm field and journal stats
    get_field_statistics()
    get_journal_statistics()
    
    # Warm search filters
    get_search_filter_counts()
    
    print("✅ Cache warmed successfully")

# Performance monitoring
def get_cache_stats():
    """Get cache performance statistics"""
    if hasattr(cache, 'get_stats'):
        return cache.get_stats()
    return {'status': 'Cache stats not available'} 