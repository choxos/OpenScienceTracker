"""
REST API Serializers for Open Science Tracker

These serializers convert Django model instances to JSON for the REST API,
providing clean and consistent data structures for external researchers.
"""

from rest_framework import serializers
from django.db.models import Count, Avg
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
            'paper_count',
            'avg_transparency_score'
        ]


class PaperSerializer(serializers.ModelSerializer):
    """
    Comprehensive paper serializer with transparency data and journal info
    """
    journal = JournalBasicSerializer(read_only=True)
    transparency_score = serializers.SerializerMethodField()
    transparency_indicators = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = [
            # Basic paper information
            'pmid',
            'title',
            'author_string',
            'pub_year',
            'journal',
            
            # Transparency data
            'transparency_score',
            'transparency_indicators',
            'is_open_data',
            'is_open_code',
            'is_coi_pred',
            'is_fund_pred',
            'is_register_pred',
            'is_report_pred',
            'is_share_pred',
            
            # Additional metadata
            'broad_subject_category',
            'abstract',
            'doi',
            'europe_pmc_id',
            'created_at',
            'updated_at'
        ]
    
    def get_transparency_score(self, obj):
        """Calculate transparency score out of 7"""
        score = 0
        score += 1 if obj.is_open_data else 0
        score += 1 if obj.is_open_code else 0
        score += 1 if obj.is_coi_pred else 0
        score += 1 if obj.is_fund_pred else 0
        score += 1 if obj.is_register_pred else 0
        score += 1 if obj.is_report_pred else 0
        score += 1 if obj.is_share_pred else 0
        return score
    
    def get_transparency_indicators(self, obj):
        """Get a summary of transparency indicators"""
        return {
            'open_data': obj.is_open_data,
            'open_code': obj.is_open_code,
            'conflict_of_interest': obj.is_coi_pred,
            'funding_declaration': obj.is_fund_pred,
            'registration': obj.is_register_pred,
            'reporting_guidelines': obj.is_report_pred,
            'data_sharing': obj.is_share_pred
        }


class PaperListSerializer(serializers.ModelSerializer):
    """
    Simplified paper serializer for list views (better performance)
    """
    journal_name = serializers.CharField(source='journal.title_abbreviation', read_only=True)
    transparency_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = [
            'pmid',
            'title',
            'author_string',
            'pub_year',
            'journal_name',
            'transparency_score',
            'broad_subject_category',
            'doi'
        ]
    
    def get_transparency_score(self, obj):
        """Calculate transparency score out of 7"""
        score = 0
        score += 1 if obj.is_open_data else 0
        score += 1 if obj.is_open_code else 0
        score += 1 if obj.is_coi_pred else 0
        score += 1 if obj.is_fund_pred else 0
        score += 1 if obj.is_register_pred else 0
        score += 1 if obj.is_report_pred else 0
        score += 1 if obj.is_share_pred else 0
        return score


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
            'nlm_unique_id',
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
            score += 1 if paper.is_report_pred else 0
            score += 1 if paper.is_share_pred else 0
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
            'reporting_percentage': round((papers.filter(is_report_pred=True).count() / total) * 100, 1),
            'sharing_percentage': round((papers.filter(is_share_pred=True).count() / total) * 100, 1)
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
            score=Avg('is_open_data') + Avg('is_open_code') + Avg('is_coi_pred') + 
                  Avg('is_fund_pred') + Avg('is_register_pred') + Avg('is_report_pred') + 
                  Avg('is_share_pred')
        )['score'] or 0, 2)


class ResearchFieldSerializer(serializers.ModelSerializer):
    """
    Comprehensive research field serializer with statistics
    """
    
    class Meta:
        model = ResearchField
        fields = [
            'id',
            'name',
            'description',
            'paper_count',
            'avg_transparency_score',
            'transparency_breakdown',
            'top_journals',
            'created_at',
            'updated_at'
        ]
        
    def to_representation(self, instance):
        """Add computed fields to the representation"""
        data = super().to_representation(instance)
        
        # Add transparency breakdown
        data['transparency_breakdown'] = self.get_transparency_breakdown(instance)
        
        # Add top journals in this field
        data['top_journals'] = self.get_top_journals(instance)
        
        return data
    
    def get_transparency_breakdown(self, obj):
        """Get transparency statistics for this research field"""
        # This would require a more complex query to get papers by research field
        # For now, return basic stats
        return {
            'open_data': 0,
            'open_code': 0,
            'conflict_of_interest': 0,
            'funding_declaration': 0,
            'registration': 0,
            'reporting_guidelines': 0,
            'data_sharing': 0
        }
    
    def get_top_journals(self, obj):
        """Get top 5 journals publishing in this research field"""
        # This would require a relationship between papers and research fields
        # For now, return empty list
        return []


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