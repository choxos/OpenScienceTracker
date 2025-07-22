from django.contrib import admin
from django.db.models import Count, Avg
from django.utils.html import format_html
from .models import Journal, Paper, ResearchField, UserProfile, TransparencyTrend

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['title_abbreviation', 'title_full', 'country', 'publisher', 
                   'publication_start_year', 'paper_count', 'is_dental_journal']
    list_filter = ['country', 'language', 'publication_start_year', 'indexing_status']
    search_fields = ['title_abbreviation', 'title_full', 'publisher', 'nlm_id']
    readonly_fields = ['created_at', 'updated_at']
    
    def paper_count(self, obj):
        return obj.papers.count()
    paper_count.short_description = 'Papers'
    
    def is_dental_journal(self, obj):
        return obj.is_dental_journal()
    is_dental_journal.boolean = True
    is_dental_journal.short_description = 'Dental'

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ['pmid', 'title_short', 'journal', 'pub_year', 'transparency_score',
                   'transparency_indicators', 'created_at']
    list_filter = ['pub_year', 'is_open_data', 'is_open_code', 'is_coi_pred', 
                  'is_fund_pred', 'is_register_pred', 'journal__country']
    search_fields = ['pmid', 'title', 'author_string', 'journal__title_abbreviation']
    readonly_fields = ['transparency_score', 'transparency_score_pct', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def title_short(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'
    
    def transparency_indicators(self, obj):
        indicators = []
        if obj.is_open_data:
            indicators.append('📊 Data')
        if obj.is_open_code:
            indicators.append('💻 Code')
        if obj.is_coi_pred:
            indicators.append('⚖️ COI')
        if obj.is_fund_pred:
            indicators.append('💰 Fund')
        if obj.is_register_pred:
            indicators.append('📝 Reg')
        
        return ' '.join(indicators) if indicators else '❌ None'
    transparency_indicators.short_description = 'Indicators'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pmid', 'pmcid', 'doi', 'title', 'author_string', 'journal', 'journal_title')
        }),
        ('Publication Details', {
            'fields': ('pub_year', 'pub_year_modified', 'first_publication_date', 
                      'year_first_pub', 'month_first_pub')
        }),
        ('Transparency Indicators', {
            'fields': (
                ('is_open_data', 'disc_data'),
                ('is_open_code', 'disc_code'),
                ('is_coi_pred', 'disc_coi'),
                ('is_fund_pred', 'disc_fund'),
                ('is_register_pred', 'disc_register'),
                ('is_replication', 'disc_replication'),
                ('is_novelty', 'disc_novelty'),
            )
        }),
        ('Calculated Metrics', {
            'fields': ('transparency_score', 'transparency_score_pct'),
            'classes': ('collapse',)
        }),
        ('Assessment Info', {
            'fields': ('assessment_date', 'assessment_tool', 'ost_version'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(ResearchField)
class ResearchFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_field', 'total_journals', 'total_papers', 'avg_transparency_score']
    list_filter = ['parent_field']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'institution', 'is_researcher', 'orcid', 'research_fields_list']
    list_filter = ['is_researcher', 'email_notifications']
    search_fields = ['user__username', 'user__email', 'institution', 'orcid']
    readonly_fields = ['created_at', 'updated_at']
    
    def research_fields_list(self, obj):
        return ', '.join([field.name for field in obj.research_interests.all()[:3]])
    research_fields_list.short_description = 'Research Interests'

@admin.register(TransparencyTrend)
class TransparencyTrendAdmin(admin.ModelAdmin):
    list_display = ['field', 'year', 'month', 'total_papers', 'avg_transparency_score',
                   'data_sharing_pct', 'code_sharing_pct']
    list_filter = ['year', 'field']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('field')

# Customize admin site
admin.site.site_header = "Open Science Tracker Admin"
admin.site.site_title = "OST Admin"
admin.site.index_title = "Welcome to Open Science Tracker Administration"

# Admin actions
def recalculate_transparency_scores(modeladmin, request, queryset):
    for paper in queryset:
        paper.save()  # This will trigger recalculation
    modeladmin.message_user(request, f"Recalculated transparency scores for {queryset.count()} papers.")

recalculate_transparency_scores.short_description = "Recalculate transparency scores"

# Add the action to PaperAdmin
PaperAdmin.actions = [recalculate_transparency_scores]
