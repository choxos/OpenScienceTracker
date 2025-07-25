"""
REST API Serializers for Open Science Tracker

These serializers convert Django model instances to JSON for the REST API,
providing clean and consistent data structures for external researchers.
"""

from rest_framework import serializers
from django.db.models import Count, Avg, Case, When, Value, IntegerField
from .models import Paper, Journal, ResearchField


class JournalBasicSerializer(serializers.ModelSerializer):
    """Basic journal information for nested relationships"""
    paper_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = [
            'id', 
            'title_abbreviation', 
            'title_full',
            'publisher',
            'country',
            'language',
            'issn_print',
            'issn_electronic',
            'paper_count'
        ]
    
    def get_paper_count(self, obj):
        """Get the number of papers in this journal"""
        return obj.papers.count()


class ResearchFieldBasicSerializer(serializers.ModelSerializer):
    """Basic research field information for nested relationships"""
    
    class Meta:
        model = ResearchField
        fields = [
            'id',
            'name',
            'total_papers',
            'avg_transparency_score'
        ]


class PaperSerializer(serializers.ModelSerializer):
    """
    Comprehensive paper serializer with EuropePMC data and transparency indicators
    """
    journal = JournalBasicSerializer(read_only=True)
    transparency_score = serializers.SerializerMethodField()
    transparency_indicators = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = [
            # Identifiers
            'epmc_id',
            'source',
            'pmid',
            'pmcid',
            'doi',
            'identifiers',
            
            # Basic paper information
            'title',
            'author_string',
            'pub_year',
            'journal',
            'journal_title',
            'journal_issn',
            'broad_subject_term',
            
            # Publication details
            'issue',
            'journal_volume',
            'page_info',
            'pub_type',
            'first_publication_date',
            'first_index_date',
            
            # Availability flags
            'is_open_access',
            'in_epmc',
            'in_pmc',
            'has_pdf',
            'has_book',
            'has_suppl',
            'cited_by_count',
            
            # Transparency indicators
            'transparency_score',
            'transparency_indicators',
            'is_coi_pred',
            'coi_text',
            'is_fund_pred',
            'fund_text',
            'is_register_pred',
            'register_text',
            'is_open_data',
            'open_data_category',
            'open_data_statements',
            'is_open_code',
            'open_code_statements',
            
            # Processing metadata
            'transparency_processed',
            'processing_date',
            'assessment_tool',
            'created_at',
            'updated_at'
        ]
    
    def get_transparency_score(self, obj):
        """Get calculated transparency score (out of 6)"""
        return obj.transparency_score
    
    def get_identifiers(self, obj):
        """Get all available identifiers"""
        return obj.get_identifiers_dict()
    
    def get_transparency_indicators(self, obj):
        """Get a summary of transparency indicators"""
        return {
            'conflict_of_interest': obj.is_coi_pred,
            'funding_declaration': obj.is_fund_pred,
            'registration': obj.is_register_pred,
            'open_data': obj.is_open_data,
            'open_code': obj.is_open_code,
            'open_access': obj.is_open_access,
        }


class PaperListSerializer(serializers.ModelSerializer):
    """
    Simplified paper serializer for list views (better performance)
    """
    journal_name = serializers.CharField(source='journal.title_abbreviation', read_only=True)
    
    class Meta:
        model = Paper
        fields = [
            'epmc_id',
            'pmid',
            'pmcid',
            'title',
            'author_string',
            'pub_year',
            'journal_name',
            'journal_title',
            'broad_subject_term',
            'transparency_score',
            'is_open_access',
            'transparency_processed',
            'assessment_tool',
            'doi'
        ]


class JournalSerializer(serializers.ModelSerializer):
    """
    Comprehensive journal serializer with statistics
    """
    paper_count = serializers.SerializerMethodField()
    avg_transparency_score = serializers.SerializerMethodField()
    transparency_stats = serializers.SerializerMethodField()
    recent_papers = serializers.SerializerMethodField()
    subject_areas = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = [
            # Basic journal information
            'id',
            'title_abbreviation',
            'title_full',
            'publisher',
            'country',
            'language',
            'issn_print',
            'issn_electronic',
            'nlm_id',
            'publication_start_year',
            'publication_end_year',
            'broad_subject_terms',
            
            # Statistics
            'paper_count',
            'avg_transparency_score',
            'transparency_stats',
            'subject_areas',
            'recent_papers',
            
            # Metadata
            'created_at',
            'updated_at'
        ]
    
    def get_paper_count(self, obj):
        """Get total number of papers in this journal"""
        return obj.papers.count()
    
    def get_avg_transparency_score(self, obj):
        """Calculate average transparency score for papers in this journal"""
        papers = obj.papers.all()
        if not papers:
            return 0
        
        total_score = 0
        count = 0
        for paper in papers:
            score = 0
            score += 1 if paper.is_open_data else 0
            score += 1 if paper.is_open_code else 0
            score += 1 if paper.is_coi_pred else 0
            score += 1 if paper.is_fund_pred else 0
            score += 1 if paper.is_register_pred else 0
            # score += 1 if paper.is_report_pred else 0  # Field doesn't exist
            # score += 1 if paper.is_share_pred else 0   # Field doesn't exist
            total_score += score
            count += 1
        
        return round(total_score / count, 2) if count > 0 else 0
    
    def get_transparency_stats(self, obj):
        """Get detailed transparency statistics for this journal"""
        papers = obj.papers.all()
        total = papers.count()
        
        if total == 0:
            return {}
        
        return {
            'total_papers': total,
            'open_data_percentage': round((papers.filter(is_open_data=True).count() / total) * 100, 1),
            'open_code_percentage': round((papers.filter(is_open_code=True).count() / total) * 100, 1),
            'coi_percentage': round((papers.filter(is_coi_pred=True).count() / total) * 100, 1),
            'funding_percentage': round((papers.filter(is_fund_pred=True).count() / total) * 100, 1),
            'registration_percentage': round((papers.filter(is_register_pred=True).count() / total) * 100, 1),
            # 'reporting_percentage': round((papers.filter(is_report_pred=True).count() / total) * 100, 1),  # Field doesn't exist
            # 'sharing_percentage': round((papers.filter(is_share_pred=True).count() / total) * 100, 1)      # Field doesn't exist
        }
    
    def get_recent_papers(self, obj):
        """Get 5 most recent papers from this journal"""
        recent = obj.papers.order_by('-pub_year', '-id')[:5]
        return PaperListSerializer(recent, many=True).data
    
    def get_subject_areas(self, obj):
        """Parse and return subject areas as a list"""
        if obj.broad_subject_terms:
            return [area.strip() for area in obj.broad_subject_terms.split(';') if area.strip()]
        return []


class JournalListSerializer(serializers.ModelSerializer):
    """
    Simplified journal serializer for list views (better performance)
    """
    paper_count = serializers.SerializerMethodField()
    avg_transparency_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = [
            'id',
            'title_abbreviation',
            'title_full',
            'publisher',
            'country',
            'paper_count',
            'avg_transparency_score'
        ]
    
    def get_paper_count(self, obj):
        return obj.papers.count()
    
    def get_avg_transparency_score(self, obj):
        """Quick calculation without loading all papers"""
        papers = obj.papers.all()
        if not papers.exists():
            return 0
        
        # This is a simplified calculation for list view performance
        return round(papers.aggregate(
            score=Avg(
                Case(When(is_open_data=True, then=Value(1)), default=Value(0), output_field=IntegerField()) +
                Case(When(is_open_code=True, then=Value(1)), default=Value(0), output_field=IntegerField()) +
                Case(When(is_coi_pred=True, then=Value(1)), default=Value(0), output_field=IntegerField()) +
                Case(When(is_fund_pred=True, then=Value(1)), default=Value(0), output_field=IntegerField()) +
                Case(When(is_register_pred=True, then=Value(1)), default=Value(0), output_field=IntegerField()) +
                Case(When(is_open_access=True, then=Value(1)), default=Value(0), output_field=IntegerField())
            )
        )['score'] or 0, 2)


class ResearchFieldSerializer(serializers.ModelSerializer):
    """
    Comprehensive research field serializer with statistics
    """
    transparency_breakdown = serializers.SerializerMethodField()
    top_journals = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchField
        fields = [
            'id',
            'name',
            'description',
            'total_papers',
            'total_journals', 
            'avg_transparency_score',
            'avg_data_sharing',
            'avg_code_sharing',
            'avg_coi_disclosure',
            'avg_funding_disclosure',
            'avg_protocol_registration',
            'avg_open_access',
            'transparency_breakdown',
            'top_journals',
            'created_at',
            'updated_at'
        ]
    
    def get_transparency_breakdown(self, obj):
        """Get transparency statistics for this research field"""
        # Get papers with this broad subject term
        papers = Paper.objects.filter(broad_subject_term=obj.name)
        total = papers.count()
        
        if total == 0:
            return {
                'open_data': 0,
                'open_code': 0,
                'conflict_of_interest': 0,
                'funding_declaration': 0,
                'registration': 0,
                'open_access': 0
            }
        
        return {
            'open_data': papers.filter(is_open_data=True).count(),
            'open_code': papers.filter(is_open_code=True).count(),
            'conflict_of_interest': papers.filter(is_coi_pred=True).count(),
            'funding_declaration': papers.filter(is_fund_pred=True).count(),
            'registration': papers.filter(is_register_pred=True).count(),
            'open_access': papers.filter(is_open_access=True).count()
        }
    
    def get_top_journals(self, obj):
        """Get top 5 journals publishing in this research field"""
        # Get papers with this broad subject term and count by journal
        from django.db.models import Count
        
        top_journals = Paper.objects.filter(
            broad_subject_term=obj.name,
            journal__isnull=False
        ).values(
            'journal__title_abbreviation',
            'journal__id'
        ).annotate(
            paper_count=Count('id')
        ).order_by('-paper_count')[:5]
        
        return [
            {
                'name': journal['journal__title_abbreviation'],
                'id': journal['journal__id'],
                'paper_count': journal['paper_count']
            }
            for journal in top_journals
        ]


class APIStatsSerializer(serializers.Serializer):
    """
    Serializer for overall API statistics
    """
    total_papers = serializers.IntegerField()
    total_journals = serializers.IntegerField()
    total_research_fields = serializers.IntegerField()
    avg_transparency_score = serializers.FloatField()
    transparency_breakdown = serializers.DictField()
    recent_papers_count = serializers.IntegerField()
    date_range = serializers.DictField()
    top_journals = serializers.ListField()
    top_research_fields = serializers.ListField() 