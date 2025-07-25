"""
Optimized Database Managers for Open Science Tracker

These managers provide pre-optimized querysets to reduce N+1 problems
and improve database performance for common operations.
"""

from django.db import models
from django.db.models import Count, Avg, Q, Prefetch
from django.core.cache import cache
from django.conf import settings

class OptimizedPaperManager(models.Manager):
    """Optimized manager for Paper model with intelligent query optimization"""
    
    def get_queryset(self):
        """Base queryset with common optimizations"""
        return super().get_queryset().select_related('journal')
    
    def for_list_view(self):
        """Optimized queryset for list views with minimal data"""
        return self.select_related('journal').only(
            # Paper fields needed for list view
            'epmc_id', 'title', 'author_string', 'pub_year', 'doi',
            'transparency_score', 'is_open_data', 'is_open_code', 
            'is_coi_pred', 'is_fund_pred', 'is_register_pred', 'is_open_access',
            'journal_title', 'created_at',
            # Journal fields needed
            'journal__title_abbreviation', 'journal__title_full'
        )
    
    def for_detail_view(self):
        """Optimized queryset for detail views with full data"""
        return self.select_related('journal').prefetch_related(
            'journal__papers'  # For related papers in journal
        )
    
    def with_transparency_scores(self):
        """Papers with calculated transparency metrics"""
        return self.annotate(
            transparency_score_pct=(models.F('transparency_score') * 100.0 / 6.0)
        )
    
    def high_transparency(self, threshold=4):
        """Papers with high transparency scores"""
        return self.filter(transparency_score__gte=threshold)
    
    def recent_papers(self, years=5):
        """Papers published in recent years"""
        from django.utils import timezone
        current_year = timezone.now().year
        return self.filter(pub_year__gte=current_year - years)
    
    def by_year_range(self, start_year=None, end_year=None):
        """Filter papers by year range"""
        queryset = self.get_queryset()
        if start_year:
            queryset = queryset.filter(pub_year__gte=start_year)
        if end_year:
            queryset = queryset.filter(pub_year__lte=end_year)
        return queryset
    
    def with_open_data(self):
        """Papers with open data"""
        return self.filter(is_open_data=True)
    
    def with_open_code(self):
        """Papers with open code"""
        return self.filter(is_open_code=True)
    
    def transparent_papers(self):
        """Papers meeting multiple transparency criteria"""
        return self.filter(
            Q(is_open_data=True) | 
            Q(is_open_code=True) | 
            Q(is_coi_pred=True) |
            Q(is_fund_pred=True)
        ).distinct()
    
    def search(self, query):
        """Optimized full-text search"""
        if not query:
            return self.none()
        
        # Cache search results for common queries
        cache_key = f"search_{hash(query.lower())}"
        cached_ids = cache.get(cache_key)
        
        if cached_ids is not None:
            return self.filter(id__in=cached_ids)
        
        # Perform search
        results = self.filter(
            Q(title__icontains=query) |
            Q(author_string__icontains=query) |
            Q(journal_title__icontains=query) |
            Q(pmid__icontains=query) |
            Q(doi__icontains=query) |
            Q(journal__title_abbreviation__icontains=query) |
            Q(journal__title_full__icontains=query)
        ).distinct()
        
        # Cache the IDs for 5 minutes
        result_ids = list(results.values_list('id', flat=True))
        cache.set(cache_key, result_ids, 300)
        
        return results
    
    def statistics_aggregate(self):
        """Get comprehensive statistics in a single query"""
        return self.aggregate(
            total=Count('id'),
            avg_transparency=Avg('transparency_score'),
            open_data_count=Count('id', filter=Q(is_open_data=True)),
            open_code_count=Count('id', filter=Q(is_open_code=True)),
            coi_count=Count('id', filter=Q(is_coi_pred=True)),
            funding_count=Count('id', filter=Q(is_fund_pred=True)),
            registration_count=Count('id', filter=Q(is_register_pred=True)),
            open_access_count=Count('id', filter=Q(is_open_access=True)),
        )

class OptimizedJournalManager(models.Manager):
    """Optimized manager for Journal model"""
    
    def get_queryset(self):
        """Base queryset with paper statistics"""
        return super().get_queryset().annotate(
            paper_count=Count('papers'),
            avg_transparency_score=Avg('papers__transparency_score')
        )
    
    def with_papers(self):
        """Journals that have papers"""
        return self.filter(paper_count__gt=0)
    
    def top_journals(self, limit=50):
        """Top journals by paper count"""
        return self.with_papers().order_by('-paper_count')[:limit]
    
    def by_subject(self, subject):
        """Journals by subject area"""
        return self.filter(broad_subject_terms__icontains=subject)
    
    def search(self, query):
        """Search journals by title or publisher"""
        if not query:
            return self.none()
        
        return self.filter(
            Q(title_abbreviation__icontains=query) |
            Q(title_full__icontains=query) |
            Q(publisher__icontains=query)
        )

class OptimizedResearchFieldManager(models.Manager):
    """Optimized manager for ResearchField model"""
    
    def get_queryset(self):
        """Base queryset ordered by activity"""
        return super().get_queryset().order_by('-total_papers', 'name')
    
    def active_fields(self):
        """Fields with papers"""
        return self.filter(total_papers__gt=0)
    
    def top_fields(self, limit=20):
        """Top research fields by paper count"""
        return self.active_fields()[:limit]
    
    def with_transparency_averages(self):
        """Fields with transparency indicator averages"""
        return self.exclude(
            avg_transparency_score__isnull=True
        ).exclude(
            avg_transparency_score=0
        )

# Performance monitoring manager
class PerformanceQueryManager(models.Manager):
    """Manager for tracking query performance"""
    
    def slow_queries(self):
        """Identify potentially slow queries - development helper"""
        from django.db import connection
        if hasattr(connection, 'queries'):
            slow_queries = [
                q for q in connection.queries 
                if float(q.get('time', 0)) > 0.1  # > 100ms
            ]
            return slow_queries
        return []
    
    def query_count(self):
        """Get total query count for current request"""
        from django.db import connection
        return len(connection.queries) if hasattr(connection, 'queries') else 0

# Bulk operations manager
class BulkOperationsManager(models.Manager):
    """Manager for efficient bulk operations"""
    
    def bulk_create_optimized(self, objects, batch_size=1000, ignore_conflicts=True):
        """Optimized bulk create with batching"""
        results = []
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            results.extend(
                self.bulk_create(batch, ignore_conflicts=ignore_conflicts)
            )
        return results
    
    def bulk_update_optimized(self, objects, fields, batch_size=1000):
        """Optimized bulk update with batching"""
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            self.bulk_update(batch, fields)
    
    def batch_delete(self, queryset, batch_size=1000):
        """Delete records in batches to avoid memory issues"""
        while True:
            batch_ids = list(
                queryset.values_list('pk', flat=True)[:batch_size]
            )
            if not batch_ids:
                break
            self.filter(pk__in=batch_ids).delete()

# Cache invalidation manager
class CacheManager:
    """Manager for cache operations related to models"""
    
    @staticmethod
    def invalidate_paper_caches():
        """Invalidate caches when papers are modified"""
        from .cache_utils import invalidate_stats_cache
        invalidate_stats_cache()
    
    @staticmethod
    def invalidate_journal_caches():
        """Invalidate caches when journals are modified"""
        cache.delete_many([
            'journal_stats_*',
            'home_stats_*',
            'search_counts_*'
        ])
    
    @staticmethod
    def warm_common_caches():
        """Warm up commonly accessed caches"""
        from .cache_utils import warm_cache
        warm_cache()

# Signal handlers for cache invalidation
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender='tracker.Paper')
def invalidate_paper_cache(sender, **kwargs):
    """Invalidate paper-related caches when papers change"""
    CacheManager.invalidate_paper_caches()

@receiver([post_save, post_delete], sender='tracker.Journal') 
def invalidate_journal_cache(sender, **kwargs):
    """Invalidate journal-related caches when journals change"""
    CacheManager.invalidate_journal_caches()

@receiver([post_save, post_delete], sender='tracker.ResearchField')
def invalidate_field_cache(sender, **kwargs):
    """Invalidate field-related caches when fields change"""
    from .cache_utils import invalidate_stats_cache
    invalidate_stats_cache() 