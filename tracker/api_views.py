"""
REST API Views for Open Science Tracker

These views provide RESTful endpoints for accessing transparency and 
reproducibility data from medical and dental literature.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.db.models import Count, Avg, Q, Max, Min
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Paper, Journal, ResearchField
from .serializers import (
    PaperSerializer, PaperListSerializer,
    JournalSerializer, JournalListSerializer, JournalBasicSerializer,
    ResearchFieldSerializer, ResearchFieldBasicSerializer,
    APIStatsSerializer
)


# =============================================================================
# FILTERS
# =============================================================================

class PaperFilter(django_filters.FilterSet):
    """Advanced filtering for papers"""
    
    # Year range filtering
    pub_year = django_filters.NumberFilter()
    pub_year__gte = django_filters.NumberFilter(field_name='pub_year', lookup_expr='gte')
    pub_year__lte = django_filters.NumberFilter(field_name='pub_year', lookup_expr='lte')
    pub_year_range = django_filters.RangeFilter(field_name='pub_year')
    
    # Journal filtering
    journal = django_filters.NumberFilter(field_name='journal__id')
    journal_name = django_filters.CharFilter(field_name='journal__title_abbreviation', lookup_expr='icontains')
    
    # Transparency filtering
    transparency_score = django_filters.NumberFilter(method='filter_transparency_score')
    transparency_score__gte = django_filters.NumberFilter(method='filter_transparency_score_gte')
    transparency_score__lte = django_filters.NumberFilter(method='filter_transparency_score_lte')
    
    # Subject category
    subject_category = django_filters.CharFilter(field_name='broad_subject_category', lookup_expr='icontains')
    
    # Boolean transparency indicators
    has_open_data = django_filters.BooleanFilter(field_name='is_open_data')
    has_open_code = django_filters.BooleanFilter(field_name='is_open_code')
    has_coi = django_filters.BooleanFilter(field_name='is_coi_pred')
    has_funding = django_filters.BooleanFilter(field_name='is_fund_pred')
    has_registration = django_filters.BooleanFilter(field_name='is_register_pred')
    has_reporting = django_filters.BooleanFilter(field_name='is_report_pred')
    has_sharing = django_filters.BooleanFilter(field_name='is_share_pred')
    
    # Author filtering
    author = django_filters.CharFilter(field_name='author_string', lookup_expr='icontains')
    
    class Meta:
        model = Paper
        fields = []
    
    def filter_transparency_score(self, queryset, name, value):
        """Filter by exact transparency score"""
        return queryset.extra(
            where=["(CASE WHEN is_open_data THEN 1 ELSE 0 END + "
                   "CASE WHEN is_open_code THEN 1 ELSE 0 END + "
                   "CASE WHEN is_coi_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_fund_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_register_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_report_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_share_pred THEN 1 ELSE 0 END) = %s"],
            params=[value]
        )
    
    def filter_transparency_score_gte(self, queryset, name, value):
        """Filter by minimum transparency score"""
        return queryset.extra(
            where=["(CASE WHEN is_open_data THEN 1 ELSE 0 END + "
                   "CASE WHEN is_open_code THEN 1 ELSE 0 END + "
                   "CASE WHEN is_coi_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_fund_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_register_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_report_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_share_pred THEN 1 ELSE 0 END) >= %s"],
            params=[value]
        )
    
    def filter_transparency_score_lte(self, queryset, name, value):
        """Filter by maximum transparency score"""
        return queryset.extra(
            where=["(CASE WHEN is_open_data THEN 1 ELSE 0 END + "
                   "CASE WHEN is_open_code THEN 1 ELSE 0 END + "
                   "CASE WHEN is_coi_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_fund_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_register_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_report_pred THEN 1 ELSE 0 END + "
                   "CASE WHEN is_share_pred THEN 1 ELSE 0 END) <= %s"],
            params=[value]
        )


class JournalFilter(django_filters.FilterSet):
    """Advanced filtering for journals"""
    
    # Basic filters
    country = django_filters.CharFilter(lookup_expr='icontains')
    publisher = django_filters.CharFilter(lookup_expr='icontains')
    language = django_filters.CharFilter(lookup_expr='icontains')
    
    # Subject terms
    subject_terms = django_filters.CharFilter(field_name='broad_subject_terms', lookup_expr='icontains')
    
    # Paper count filtering
    min_papers = django_filters.NumberFilter(method='filter_min_papers')
    max_papers = django_filters.NumberFilter(method='filter_max_papers')
    
    # Year range
    start_year = django_filters.NumberFilter(field_name='publication_start_year')
    start_year__gte = django_filters.NumberFilter(field_name='publication_start_year', lookup_expr='gte')
    start_year__lte = django_filters.NumberFilter(field_name='publication_start_year', lookup_expr='lte')
    
    class Meta:
        model = Journal
        fields = []
    
    def filter_min_papers(self, queryset, name, value):
        """Filter journals with minimum number of papers"""
        return queryset.annotate(paper_count=Count('papers')).filter(paper_count__gte=value)
    
    def filter_max_papers(self, queryset, name, value):
        """Filter journals with maximum number of papers"""
        return queryset.annotate(paper_count=Count('papers')).filter(paper_count__lte=value)


# =============================================================================
# VIEWSETS
# =============================================================================

@extend_schema_view(
    list=extend_schema(
        description="List all research papers with filtering and search capabilities",
        parameters=[
            OpenApiParameter("pub_year", description="Filter by publication year"),
            OpenApiParameter("pub_year__gte", description="Papers published after this year"),
            OpenApiParameter("pub_year__lte", description="Papers published before this year"),
            OpenApiParameter("journal", description="Filter by journal ID"),
            OpenApiParameter("journal_name", description="Filter by journal name (partial match)"),
            OpenApiParameter("transparency_score__gte", description="Minimum transparency score (0-7)"),
            OpenApiParameter("has_open_data", description="Filter papers with open data"),
            OpenApiParameter("author", description="Filter by author name (partial match)"),
            OpenApiParameter("subject_category", description="Filter by subject category"),
            OpenApiParameter("search", description="Search in title and abstract"),
        ]
    ),
    retrieve=extend_schema(description="Get detailed information about a specific paper"),
)
class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for research papers with transparency data
    
    Provides endpoints to:
    - List all papers with advanced filtering
    - Retrieve detailed paper information
    - Search papers by title, abstract, or author
    - Filter by transparency indicators
    """
    
    queryset = Paper.objects.select_related('journal').all()
    filterset_class = PaperFilter
    search_fields = ['title', 'abstract', 'author_string']
    ordering_fields = ['pub_year', 'pmid', 'created_at']
    ordering = ['-pub_year', '-id']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return PaperListSerializer
        return PaperSerializer
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @action(detail=False, methods=['get'])
    def transparency_stats(self, request):
        """Get overall transparency statistics for papers"""
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        
        if total == 0:
            return Response({
                'message': 'No papers found with the given filters',
                'total_papers': 0
            })
        
        stats = {
            'total_papers': total,
            'transparency_indicators': {
                'open_data': {
                    'count': queryset.filter(is_open_data=True).count(),
                    'percentage': round((queryset.filter(is_open_data=True).count() / total) * 100, 1)
                },
                'open_code': {
                    'count': queryset.filter(is_open_code=True).count(),
                    'percentage': round((queryset.filter(is_open_code=True).count() / total) * 100, 1)
                },
                'conflict_of_interest': {
                    'count': queryset.filter(is_coi_pred=True).count(),
                    'percentage': round((queryset.filter(is_coi_pred=True).count() / total) * 100, 1)
                },
                'funding_declaration': {
                    'count': queryset.filter(is_fund_pred=True).count(),
                    'percentage': round((queryset.filter(is_fund_pred=True).count() / total) * 100, 1)
                },
                'registration': {
                    'count': queryset.filter(is_register_pred=True).count(),
                    'percentage': round((queryset.filter(is_register_pred=True).count() / total) * 100, 1)
                },
                'reporting_guidelines': {
                    'count': queryset.filter(is_report_pred=True).count(),
                    'percentage': round((queryset.filter(is_report_pred=True).count() / total) * 100, 1)
                },
                'data_sharing': {
                    'count': queryset.filter(is_share_pred=True).count(),
                    'percentage': round((queryset.filter(is_share_pred=True).count() / total) * 100, 1)
                }
            },
            'year_range': {
                'earliest': queryset.aggregate(min_year=Min('pub_year'))['min_year'],
                'latest': queryset.aggregate(max_year=Max('pub_year'))['max_year']
            }
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def by_year(self, request):
        """Get paper counts by publication year"""
        queryset = self.filter_queryset(self.get_queryset())
        
        year_stats = queryset.values('pub_year').annotate(
            count=Count('id')
        ).order_by('pub_year')
        
        return Response(list(year_stats))


@extend_schema_view(
    list=extend_schema(
        description="List all journals with paper counts and transparency statistics",
        parameters=[
            OpenApiParameter("country", description="Filter by country"),
            OpenApiParameter("publisher", description="Filter by publisher name"),
            OpenApiParameter("min_papers", description="Minimum number of papers in journal"),
            OpenApiParameter("subject_terms", description="Filter by subject terms"),
            OpenApiParameter("search", description="Search journal names"),
        ]
    ),
    retrieve=extend_schema(description="Get detailed journal information with statistics"),
)
class JournalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for academic journals
    
    Provides endpoints to:
    - List all journals with statistics
    - Retrieve detailed journal information
    - Search journals by name or publisher
    - Filter by country, subject terms, etc.
    """
    
    queryset = Journal.objects.prefetch_related('papers').all()
    filterset_class = JournalFilter
    search_fields = ['title_abbreviation', 'title_full', 'publisher']
    ordering_fields = ['title_abbreviation', 'publication_start_year']
    ordering = ['title_abbreviation']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return JournalListSerializer
        return JournalSerializer
    
    @action(detail=True, methods=['get'])
    def papers(self, request, pk=None):
        """Get all papers from a specific journal"""
        journal = self.get_object()
        papers = journal.papers.all()
        
        # Apply paper filters if provided
        filter_backend = DjangoFilterBackend()
        papers = filter_backend.filter_queryset(request, papers, PaperViewSet)
        
        # Paginate results
        page = self.paginate_queryset(papers)
        if page is not None:
            serializer = PaperListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PaperListSerializer(papers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_publishers(self, request):
        """Get top publishers by journal count"""
        publishers = Journal.objects.values('publisher').annotate(
            journal_count=Count('id'),
            total_papers=Count('papers')
        ).filter(
            publisher__isnull=False
        ).order_by('-journal_count')[:20]
        
        return Response(list(publishers))


@extend_schema_view(
    list=extend_schema(description="List all research fields with statistics"),
    retrieve=extend_schema(description="Get detailed research field information"),
)
class ResearchFieldViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for research fields (broad subject categories)
    
    Provides endpoints to:
    - List all research fields
    - Retrieve detailed field information
    - Get statistics by research area
    """
    
    queryset = ResearchField.objects.all()
    serializer_class = ResearchFieldSerializer
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'paper_count', 'avg_transparency_score']
    ordering = ['name']


# =============================================================================
# STATISTICS AND OVERVIEW ENDPOINTS
# =============================================================================

from rest_framework.views import APIView
from django.shortcuts import render

class APIOverviewView(APIView):
    """
    API Overview with general statistics and available endpoints
    """
    
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    def get(self, request):
        """Get overall API statistics and information"""
        
        # Basic counts
        total_papers = Paper.objects.count()
        total_journals = Journal.objects.count()
        total_research_fields = ResearchField.objects.count()
        
        # Transparency statistics
        transparency_stats = {
            'open_data': Paper.objects.filter(is_open_data=True).count(),
            'open_code': Paper.objects.filter(is_open_code=True).count(),
            'conflict_of_interest': Paper.objects.filter(is_coi_pred=True).count(),
            'funding_declaration': Paper.objects.filter(is_fund_pred=True).count(),
            'registration': Paper.objects.filter(is_register_pred=True).count(),
            'reporting_guidelines': Paper.objects.filter(is_report_pred=True).count(),
            'data_sharing': Paper.objects.filter(is_share_pred=True).count()
        }
        
        # Year range
        year_range = Paper.objects.aggregate(
            earliest=Min('pub_year'),
            latest=Max('pub_year')
        )
        
        # Top journals by paper count
        top_journals = Journal.objects.annotate(
            paper_count=Count('papers')
        ).filter(paper_count__gt=0).order_by('-paper_count')[:10]
        
        # Recent activity
        recent_papers = Paper.objects.order_by('-created_at')[:5]
        
        response_data = {
            'api_info': {
                'name': 'Open Science Tracker API',
                'version': '1.0.0',
                'description': 'REST API for accessing transparency and reproducibility data from medical and dental literature',
                'documentation_url': request.build_absolute_uri('/api/docs/'),
                'contact': {
                    'name': 'Ahmad Sofi-Mahmudi',
                    'email': 'ahmad.pub@gmail.com'
                }
            },
            'statistics': {
                'total_papers': total_papers,
                'total_journals': total_journals,
                'total_research_fields': total_research_fields,
                'transparency_coverage': transparency_stats,
                'year_range': year_range,
                'last_updated': Paper.objects.aggregate(last_update=Max('updated_at'))['last_update']
            },
            'top_journals': JournalBasicSerializer(top_journals, many=True).data,
            'recent_papers': PaperListSerializer(recent_papers, many=True).data,
            'available_endpoints': {
                'papers': request.build_absolute_uri('/api/v1/papers/'),
                'journals': request.build_absolute_uri('/api/v1/journals/'),
                'research_fields': request.build_absolute_uri('/api/v1/research-fields/'),
                'paper_stats': request.build_absolute_uri('/api/v1/papers/transparency_stats/'),
                'schema': request.build_absolute_uri('/api/schema/'),
                'swagger_ui': request.build_absolute_uri('/api/docs/'),
                'redoc': request.build_absolute_uri('/api/redoc/')
            }
        }
        
        # Return HTML for browser requests, JSON for API requests
        if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
            return render(request, 'tracker/api_documentation.html', response_data)
        else:
            return Response(response_data) 