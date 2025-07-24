"""
Performance and Caching Middleware for Open Science Tracker

This module provides middleware for monitoring request performance,
caching optimization, and database query tracking.
"""

import time
import logging
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse
import json

# Set up performance logger
performance_logger = logging.getLogger('performance')


class PerformanceMonitoringMiddleware:
    """
    Middleware to monitor request performance and log slow requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 2.0)
        self.enable_query_logging = getattr(settings, 'ENABLE_QUERY_LOGGING', False)
    
    def __call__(self, request):
        # Record start time and query count
        start_time = time.time()
        start_queries = len(connection.queries) if self.enable_query_logging else 0
        
        # Process request
        response = self.get_response(request)
        
        # Calculate performance metrics
        duration = time.time() - start_time
        query_count = len(connection.queries) - start_queries if self.enable_query_logging else 0
        
        # Add performance headers
        response['X-Response-Time'] = f"{duration:.3f}s"
        if self.enable_query_logging:
            response['X-DB-Queries'] = str(query_count)
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            performance_logger.warning(
                f"Slow request detected: {request.method} {request.path} "
                f"took {duration:.3f}s with {query_count} DB queries"
            )
        
        # Log API requests for monitoring
        if request.path.startswith('/api/'):
            performance_logger.info(
                f"API request: {request.method} {request.path} "
                f"- {duration:.3f}s - {response.status_code}"
            )
        
        return response


class DatabaseQueryCountMiddleware:
    """
    Middleware to track and optimize database query usage
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_queries_warning = getattr(settings, 'MAX_QUERIES_WARNING', 20)
    
    def __call__(self, request):
        # Reset queries and record start
        connection.queries_log.clear()
        start_query_count = len(connection.queries)
        
        response = self.get_response(request)
        
        # Calculate query metrics
        query_count = len(connection.queries) - start_query_count
        
        # Warn about high query count (potential N+1 problems)
        if query_count > self.max_queries_warning:
            performance_logger.warning(
                f"High query count: {request.path} executed {query_count} queries"
            )
            
            # Log the actual queries in debug mode
            if settings.DEBUG:
                for query in connection.queries[-query_count:]:
                    performance_logger.debug(f"Query: {query['sql'][:100]}...")
        
        response['X-DB-Query-Count'] = str(query_count)
        return response


class CacheOptimizationMiddleware:
    """
    Middleware for intelligent caching of responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cacheable_paths = getattr(settings, 'CACHEABLE_PATHS', [
            '/statistics/',
            '/api/',
            '/journals/',
        ])
        self.cache_timeout = getattr(settings, 'MIDDLEWARE_CACHE_TIMEOUT', 300)
    
    def __call__(self, request):
        # Check if this path should be cached
        if not any(request.path.startswith(path) for path in self.cacheable_paths):
            return self.get_response(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            response = HttpResponse(
                cached_response['content'],
                content_type=cached_response['content_type'],
                status=cached_response['status']
            )
            response['X-Cache-Status'] = 'HIT'
            return response
        
        # Get fresh response
        response = self.get_response(request)
        
        # Cache successful responses
        if response.status_code == 200 and hasattr(response, 'content'):
            cache_data = {
                'content': response.content,
                'content_type': response.get('Content-Type', 'text/html'),
                'status': response.status_code
            }
            cache.set(cache_key, cache_data, self.cache_timeout)
            response['X-Cache-Status'] = 'MISS'
        
        return response
    
    def _generate_cache_key(self, request):
        """Generate a cache key based on request parameters"""
        key_parts = [
            request.path,
            request.GET.urlencode() if request.GET else 'no-params'
        ]
        return 'middleware_cache:' + ':'.join(key_parts)


class RequestLoggingMiddleware:
    """
    Middleware for detailed request logging and analytics
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.analytics_logger = logging.getLogger('analytics')
    
    def __call__(self, request):
        # Record request details
        request_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self._get_client_ip(request),
            'referer': request.META.get('HTTP_REFERER', ''),
        }
        
        # Process request
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        # Log analytics data
        analytics_data = {
            **request_data,
            'response_time': duration,
            'status_code': response.status_code,
            'response_size': len(response.content) if hasattr(response, 'content') else 0
        }
        
        self.analytics_logger.info(json.dumps(analytics_data))
        
        return response
    
    def _get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CompressionMiddleware:
    """
    Middleware for response compression optimization
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.min_compression_size = getattr(settings, 'MIN_COMPRESSION_SIZE', 1024)
        self.compressible_types = getattr(settings, 'COMPRESSIBLE_CONTENT_TYPES', [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/xml',
            'application/xml'
        ])
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if compression is beneficial
        if (hasattr(response, 'content') and 
            len(response.content) > self.min_compression_size and
            any(ct in response.get('Content-Type', '') for ct in self.compressible_types) and
            'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', '')):
            
            response['X-Compression-Eligible'] = 'True'
        
        return response


# Utility functions for caching
def cache_key_generator(prefix, *args, **kwargs):
    """
    Generate consistent cache keys for various operations
    """
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ':'.join(key_parts)


def invalidate_cache_pattern(pattern):
    """
    Invalidate cache keys matching a pattern
    """
    try:
        # This would require a cache backend that supports pattern deletion
        # For Redis: cache.delete_pattern(pattern)
        # For now, we'll implement a simple approach
        pass
    except AttributeError:
        # Fallback for cache backends that don't support pattern deletion
        pass


class CacheUtils:
    """
    Utility class for common caching operations
    """
    
    @staticmethod
    def get_or_set_statistics(cache_key, calculator_func, timeout=1800):
        """
        Get statistics from cache or calculate and cache them
        """
        stats = cache.get(cache_key)
        if stats is None:
            stats = calculator_func()
            cache.set(cache_key, stats, timeout)
        return stats
    
    @staticmethod
    def cache_queryset_result(queryset, cache_key, timeout=600):
        """
        Cache the result of a queryset evaluation
        """
        cached_result = cache.get(cache_key)
        if cached_result is None:
            cached_result = list(queryset)
            cache.set(cache_key, cached_result, timeout)
        return cached_result
    
    @staticmethod
    def invalidate_model_cache(model_name):
        """
        Invalidate all cache entries related to a specific model
        """
        patterns_to_invalidate = [
            f"*{model_name.lower()}*",
            f"*statistics*",
            f"*home*"
        ]
        
        for pattern in patterns_to_invalidate:
            invalidate_cache_pattern(pattern)


# Decorators for view-level performance optimization
def monitor_performance(func):
    """
    Decorator to monitor individual view performance
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        performance_logger.info(
            f"View {func.__name__} executed in {duration:.3f}s"
        )
        
        return result
    return wrapper


def cache_view_result(timeout=300, key_func=None):
    """
    Decorator to cache view results
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = f"view:{func.__name__}:{hash(str(args))}{hash(str(kwargs))}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(request, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator 