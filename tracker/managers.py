"""
Optimized Database Managers for Open Science Tracker

These managers provide pre-optimized querysets to reduce N+1 problems
and improve database performance for common operations.
"""

from django.db import models
from django.db.models import Count, Avg, Q, Prefetch, Case, When, IntegerField


class OptimizedPaperManager(models.Manager):
    """Manager with optimized querysets for papers"""
    
    def with_journal(self):
        """Papers with journal data preloaded"""
        return self.select_related('journal')
    
    def for_list_view(self):
        """Optimized queryset for list views - only load necessary fields"""
        return self.select_related('journal').only(
            'pmid', 'title', 'author_string', 'pub_year',
            'transparency_score', 'is_open_data', 'is_open_code',
            'is_coi_pred', 'is_fund_pred', 'is_register_pred',
            # 'is_report_pred', 'is_share_pred',  # Fields don't exist
            'doi', 'broad_subject_term',
            'journal__title_abbreviation', 'journal__id', 'journal__title_full'
        )
    
    def for_api_list(self):
        """Optimized queryset for API list endpoints"""
        return self.select_related('journal').only(
            'pmid', 'title', 'author_string', 'pub_year', 'doi',
            'transparency_score', 'broad_subject_term',
            'journal__title_abbreviation'
        )
    
    def for_detail_view(self):
        """Optimized queryset for detail views"""
        return self.select_related('journal').prefetch_related(
            Prefetch('journal__papers', 
                    queryset=self.get_queryset().only('pmid', 'title', 'pub_year')[:5])
        )
    
    def with_calculated_transparency_score(self):
        """Papers with calculated transparency score using database aggregation"""
        return self.annotate(
            calc_transparency_score=Case(
                When(is_open_data=True, then=1), default=0,
                output_field=IntegerField()
            ) + Case(
                When(is_open_code=True, then=1), default=0,
                output_field=IntegerField()
            ) + Case(
                When(is_coi_pred=True, then=1), default=0,
                output_field=IntegerField()
            ) + Case(
                When(is_fund_pred=True, then=1), default=0,
                output_field=IntegerField()
            ) + Case(
                When(is_register_pred=True, then=1), default=0,
                output_field=IntegerField()
            ) + Case(
                When(is_open_access=True, then=1), default=0,
                output_field=IntegerField()
            )
            # + Case(
            #     When(is_report_pred=True, then=1), default=0,  # Field doesn't exist
            #     output_field=IntegerField()
            # ) + Case(
            #     When(is_share_pred=True, then=1), default=0,   # Field doesn't exist
            #     output_field=IntegerField()
            # )
        )
    
    def recent(self, limit=10):
        """Get recent papers efficiently"""
        return self.for_list_view().order_by('-created_at')[:limit]
    
    def by_year(self, year):
        """Get papers from specific year efficiently"""
        return self.for_list_view().filter(pub_year=year)
    
    def high_transparency(self, min_score=5):
        """Get papers with high transparency scores"""
        return self.with_calculated_transparency_score().filter(
            calc_transparency_score__gte=min_score
        )
    
    def search(self, query):
        """Optimized search across papers"""
        return self.for_list_view().filter(
            Q(title__icontains=query) |
            Q(author_string__icontains=query) |
            Q(pmid__icontains=query) |
            Q(doi__icontains=query) |
            Q(journal__title_abbreviation__icontains=query) |
            Q(journal__title_full__icontains=query)
        ).distinct()


class OptimizedJournalManager(models.Manager):
    """Manager with optimized querysets for journals"""
    
    def with_paper_counts(self):
        """Journals with paper counts and transparency stats annotated"""
        return self.annotate(
            paper_count=Count('papers'),
            avg_transparency=Avg('papers__transparency_score'),
            open_data_count=Count('papers', filter=Q(papers__is_open_data=True)),
            open_code_count=Count('papers', filter=Q(papers__is_open_code=True)),
            coi_count=Count('papers', filter=Q(papers__is_coi_pred=True)),
            funding_count=Count('papers', filter=Q(papers__is_fund_pred=True))
        )
    
    def for_list_view(self):
        """Optimized queryset for journal list views"""
        return self.with_paper_counts().only(
            'id', 'title_abbreviation', 'title_full', 
            'publisher', 'country', 'issn_print', 'issn_electronic'
        ).filter(paper_count__gt=0)  # Only journals with papers
    
    def for_api_list(self):
        """Optimized queryset for API list endpoints"""
        return self.with_paper_counts().only(
            'id', 'title_abbreviation', 'title_full', 
            'publisher', 'country'
        )
    
    def for_detail_view(self):
        """Optimized queryset for journal detail views"""
        return self.prefetch_related(
            Prefetch('papers', 
                    queryset=models.Q(papers__isnull=False).only(
                        'pmid', 'title', 'pub_year', 'transparency_score',
                        'is_open_data', 'is_open_code', 'is_coi_pred'
                    ))
        )
    
    def top_by_papers(self, limit=10):
        """Top journals by paper count"""
        return self.with_paper_counts().filter(
            paper_count__gt=0
        ).order_by('-paper_count')[:limit]
    
    def by_country(self, country):
        """Journals from specific country"""
        return self.for_list_view().filter(country__icontains=country)
    
    def by_publisher(self, publisher):
        """Journals from specific publisher"""
        return self.for_list_view().filter(publisher__icontains=publisher)
    
    def with_subject(self, subject):
        """Journals containing specific subject term"""
        return self.for_list_view().filter(broad_subject_terms__icontains=subject)
    
    def search(self, query):
        """Optimized search across journals"""
        return self.for_list_view().filter(
            Q(title_abbreviation__icontains=query) |
            Q(title_full__icontains=query) |
            Q(publisher__icontains=query) |
            Q(broad_subject_terms__icontains=query)
        ).distinct()


class OptimizedResearchFieldManager(models.Manager):
    """Manager with optimized querysets for research fields"""
    
    def with_statistics(self):
        """Research fields with computed statistics"""
        return self.annotate(
            related_papers_count=Count('papers', distinct=True),
            avg_transparency=Avg('papers__transparency_score')
        )
    
    def active_fields(self):
        """Research fields that have associated papers"""
        return self.with_statistics().filter(related_papers_count__gt=0)
    
    def top_fields(self, limit=20):
        """Top research fields by paper count"""
        return self.with_statistics().filter(
            related_papers_count__gt=0
        ).order_by('-related_papers_count')[:limit]


# Mixin for adding optimized methods to existing managers
class PerformanceOptimizationMixin:
    """Mixin to add performance optimization methods to existing managers"""
    
    def bulk_create_optimized(self, objs, batch_size=1000, ignore_conflicts=False):
        """Optimized bulk create with better batch size"""
        return self.bulk_create(
            objs, 
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts
        )
    
    def bulk_update_optimized(self, objs, fields, batch_size=1000):
        """Optimized bulk update with better batch size"""
        return self.bulk_update(objs, fields, batch_size=batch_size)
    
    def iterator_chunked(self, chunk_size=2000):
        """Memory-efficient iteration over large querysets"""
        return self.iterator(chunk_size=chunk_size)


# Combined managers for models
class PaperManager(OptimizedPaperManager, PerformanceOptimizationMixin):
    """Combined paper manager with all optimizations"""
    pass


class JournalManager(OptimizedJournalManager, PerformanceOptimizationMixin):
    """Combined journal manager with all optimizations"""
    pass


class ResearchFieldManager(OptimizedResearchFieldManager, PerformanceOptimizationMixin):
    """Combined research field manager with all optimizations"""
    pass 