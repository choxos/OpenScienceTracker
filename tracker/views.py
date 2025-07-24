from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Count, Avg, Sum, Max
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
import json
import csv
import pandas as pd
from datetime import datetime

from .models import Paper, Journal, ResearchField, UserProfile, TransparencyTrend
from .forms import UserProfileForm, PaperSearchForm, JournalSearchForm

class HomeView(TemplateView):
    """Home page with overview statistics"""
    template_name = 'tracker/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic statistics
        context['total_papers'] = Paper.objects.count()
        context['total_journals'] = Journal.objects.count()
        context['dental_journals'] = Journal.objects.filter(
            broad_subject_terms__icontains='Dentistry'
        ).count()
        
        # Transparency statistics
        papers = Paper.objects.all()
        context['avg_transparency_score'] = papers.aggregate(
            avg_score=Avg('transparency_score')
        )['avg_score'] or 0
        
        context['data_sharing_pct'] = (papers.filter(is_open_data=True).count() / 
                                     max(papers.count(), 1)) * 100
        context['code_sharing_pct'] = (papers.filter(is_open_code=True).count() / 
                                     max(papers.count(), 1)) * 100
        context['coi_disclosure_pct'] = (papers.filter(is_coi_pred=True).count() / 
                                       max(papers.count(), 1)) * 100
        context['funding_disclosure_pct'] = (papers.filter(is_fund_pred=True).count() / 
                                           max(papers.count(), 1)) * 100
        context['protocol_registration_pct'] = (papers.filter(is_register_pred=True).count() / 
                                               max(papers.count(), 1)) * 100
        context['open_access_pct'] = (papers.filter(is_open_access=True).count() / 
                                     max(papers.count(), 1)) * 100
        
        # Recent papers
        context['recent_papers'] = papers.order_by('-created_at')[:5]
        
        # Top journals by paper count
        context['top_journals'] = Journal.objects.annotate(
            paper_count=Count('papers')
        ).order_by('-paper_count')[:5]
        
        return context

class AboutView(TemplateView):
    """About page explaining OST project, methodology, and team"""
    template_name = 'tracker/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic statistics for the about page
        total_papers = Paper.objects.count()
        total_journals = Journal.objects.count()
        
        # Transparency statistics
        papers = Paper.objects.all()
        avg_transparency = papers.aggregate(avg_score=Avg('transparency_score'))['avg_score'] or 0
        
        # Coverage statistics
        years_covered = papers.aggregate(
            min_year=Count('pub_year', distinct=True),
            earliest=Count('pub_year', distinct=True)
        )
        
        context.update({
            'total_papers': total_papers,
            'total_journals': total_journals,
            'avg_transparency_score': round(avg_transparency, 2),
            'data_sharing_pct': round((papers.filter(is_open_data=True).count() / max(total_papers, 1)) * 100, 1),
            'open_access_pct': round((papers.filter(is_open_access=True).count() / max(total_papers, 1)) * 100, 1),
            'dental_focus': Journal.objects.filter(broad_subject_terms__icontains='Dentistry').count(),
            'years_of_data': papers.values('pub_year').distinct().count(),
            'countries_covered': papers.exclude(journal__country__isnull=True).exclude(journal__country='').values('journal__country').distinct().count(),
        })
        
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard with personalized statistics"""
    template_name = 'tracker/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User-specific statistics based on their interests
        try:
            profile = self.request.user.userprofile
            preferred_fields = profile.preferred_fields.all()
            
            if preferred_fields:
                # Filter papers by user's preferred fields
                papers = Paper.objects.filter(
                    journal__broad_subject_terms__icontains=preferred_fields.first().name
                )
                context['user_field_papers'] = papers.count()
                context['user_field_avg_transparency'] = papers.aggregate(
                    avg_score=Avg('transparency_score')
                )['avg_score'] or 0
        except UserProfile.DoesNotExist:
            context['user_field_papers'] = 0
            context['user_field_avg_transparency'] = 0
        
        # General statistics
        context['total_papers'] = Paper.objects.count()
        context['total_journals'] = Journal.objects.count()
        
        return context

class PaperListView(ListView):
    """List view for papers with pagination and filtering"""
    model = Paper
    template_name = 'tracker/paper_list.html'
    context_object_name = 'papers'
    paginate_by = settings.OST_PAGINATION_SIZE
    
    def get_queryset(self):
        queryset = Paper.objects.select_related('journal').all()
        
        # Filter by search query
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(author_string__icontains=q) |
                Q(journal_title__icontains=q) |
                Q(pmid__icontains=q) |
                Q(doi__icontains=q)
            )
        
        # Filter by journal
        journal = self.request.GET.get('journal')
        if journal:
            queryset = queryset.filter(journal_id=journal)
        
        # Filter by subject category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(broad_subject_term=category)
            
        # Filter by broad subject term (from the new filter)
        broad_subject_term = self.request.GET.get('broad_subject_term')
        if broad_subject_term:
            queryset = queryset.filter(broad_subject_term=broad_subject_term)
        
        # Filter by publication type
        pub_type = self.request.GET.get('pub_type')
        if pub_type:
            queryset = queryset.filter(pub_type=pub_type)
        
        # Filter by year
        year = self.request.GET.get('year')
        if year:
            queryset = queryset.filter(pub_year=year)
        
        # Filter by transparency score range
        transparency = self.request.GET.get('transparency')
        if transparency == 'high':
            queryset = queryset.filter(transparency_score__gte=5)
        elif transparency == 'medium':
            queryset = queryset.filter(transparency_score__gte=3, transparency_score__lt=5)
        elif transparency == 'low':
            queryset = queryset.filter(transparency_score__lt=3)
        
        # Filter by transparency indicators
        indicators = self.request.GET.getlist('indicators')
        if 'open_data' in indicators:
            queryset = queryset.filter(is_open_data=True)
        if 'open_code' in indicators:
            queryset = queryset.filter(is_open_code=True)
        if 'coi_disclosure' in indicators:
            queryset = queryset.filter(is_coi_pred=True)
        if 'funding' in indicators:
            queryset = queryset.filter(is_fund_pred=True)
        if 'registration' in indicators:
            queryset = queryset.filter(is_register_pred=True)
        if 'open_access' in indicators:
            queryset = queryset.filter(is_open_access=True)
        
        # Ordering
        order_by = self.request.GET.get('order_by', '-pub_year')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PaperSearchForm(self.request.GET)
        context['available_years'] = Paper.objects.values_list(
            'pub_year', flat=True
        ).distinct().order_by('-pub_year')
        context['available_journals'] = Journal.objects.all().order_by('title_abbreviation')
        context['available_categories'] = Paper.objects.exclude(
            broad_subject_term__isnull=True
        ).values_list('broad_subject_term', flat=True).distinct().order_by('broad_subject_term')
        
        # Add available publication types
        context['available_pub_types'] = Paper.objects.exclude(
            pub_type__isnull=True
        ).exclude(pub_type='').values_list('pub_type', flat=True).distinct().order_by('pub_type')
        
        # Add selected indicators for template checkbox state
        context['selected_indicators'] = self.request.GET.getlist('indicators')
        
        return context

class PaperDetailView(TemplateView):
    """Detail view for individual papers"""
    template_name = 'tracker/paper_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the paper by epmc_id
        epmc_id = self.kwargs.get('epmc_id')
        if epmc_id is None:
            raise Http404("No paper epmc_id provided")
        
        try:
            paper = Paper.objects.select_related('journal').get(epmc_id=epmc_id)
        except Paper.DoesNotExist:
            raise Http404(f"No paper found with epmc_id: {epmc_id}")
        
        context['paper'] = paper
        
        # Related papers from same journal
        context['related_papers'] = []
        if paper.journal:
            try:
                context['related_papers'] = Paper.objects.filter(
                    journal=paper.journal
                ).exclude(epmc_id=paper.epmc_id)[:5]
            except:
                pass
        
        # Transparency breakdown
        context['transparency_indicators'] = [
            ('Open Data', paper.is_open_data),
            ('Open Code', paper.is_open_code),
            ('COI Disclosure', paper.is_coi_pred),
            ('Funding Disclosure', paper.is_fund_pred),
            ('Protocol Registration', paper.is_register_pred),
            ('Open Access', paper.is_open_access),
        ]
        
        return context

class PaperSearchView(TemplateView):
    """Advanced search for papers"""
    template_name = 'tracker/paper_search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PaperSearchForm()
        context['journals'] = Journal.objects.all()
        context['years'] = range(2000, datetime.now().year + 1)
        return context

class JournalListView(ListView):
    """List view for journals"""
    model = Journal
    template_name = 'tracker/journal_list.html'
    context_object_name = 'journals'
    paginate_by = settings.OST_PAGINATION_SIZE
    
    def get_queryset(self):
        queryset = Journal.objects.annotate(
            paper_count=Count('papers'),
            avg_transparency=Avg('papers__transparency_score')
        ).all()
        
        # Filter by search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title_abbreviation__icontains=search_query) |
                Q(title_full__icontains=search_query) |
                Q(publisher__icontains=search_query)
            )
        
        # Filter by subject
        subject = self.request.GET.get('subject')
        if subject:
            queryset = queryset.filter(broad_subject_terms__icontains=subject)
        
        # Filter by country
        country = self.request.GET.get('country')
        if country:
            queryset = queryset.filter(country=country)
        
        # Ordering
        order_by = self.request.GET.get('order_by', 'title_abbreviation')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = JournalSearchForm(self.request.GET)
        context['available_countries'] = Journal.objects.values_list(
            'country', flat=True
        ).distinct().order_by('country')
        context['available_subjects'] = [
            'Dentistry', 'Orthodontics', 'Medicine', 'Surgery'
        ]  # Common subjects
        return context

class JournalDetailView(DetailView):
    """Detail view for journals"""
    model = Journal
    template_name = 'tracker/journal_detail.html'
    context_object_name = 'journal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Journal statistics
        papers = self.object.papers.all()
        context['total_papers'] = papers.count()
        context['avg_transparency_score'] = papers.aggregate(
            avg_score=Avg('transparency_score')
        )['avg_score'] or 0
        
        # Transparency breakdown
        context['transparency_stats'] = {
            'data_sharing': papers.filter(is_open_data=True).count(),
            'code_sharing': papers.filter(is_open_code=True).count(),
            'coi_disclosure': papers.filter(is_coi_pred=True).count(),
            'funding_disclosure': papers.filter(is_fund_pred=True).count(),
            'protocol_registration': papers.filter(is_register_pred=True).count(),
        }
        
        # Recent papers
        context['recent_papers'] = papers.order_by('-pub_year')[:10]
        
        # Yearly trends
        context['yearly_stats'] = papers.values('pub_year').annotate(
            count=Count('id'),
            avg_transparency=Avg('transparency_score')
        ).order_by('pub_year')
        
        return context

class StatisticsView(TemplateView):
    """Main statistics page"""
    template_name = 'tracker/statistics.html'
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Overall statistics
        papers = Paper.objects.all()
        journals = Journal.objects.all()
        
        context['total_papers'] = papers.count()
        context['total_journals'] = journals.count()
        
        # Transparency indicators statistics
        indicators_stats = {}
        indicators = [
            ('data_sharing', 'is_open_data', 'Data Sharing'),
            ('code_sharing', 'is_open_code', 'Code Sharing'),
            ('coi_disclosure', 'is_coi_pred', 'COI Disclosure'),
            ('funding_disclosure', 'is_fund_pred', 'Funding Disclosure'),
            ('protocol_registration', 'is_register_pred', 'Protocol Registration'),
            ('open_access', 'is_open_access', 'Open Access'),
        ]
        
        for key, field, label in indicators:
            count = papers.filter(**{field: True}).count()
            percentage = (count / max(papers.count(), 1)) * 100
            indicators_stats[key] = {
                'count': count,
                'percentage': percentage,
                'label': label
            }
        
        context['indicators_stats'] = indicators_stats
        
        # Journal distribution by country
        context['country_distribution'] = journals.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Papers by year
        context['yearly_distribution'] = papers.values('pub_year').annotate(
            count=Count('id'),
            avg_transparency=Avg('transparency_score')
        ).order_by('pub_year')
        
        # Category-based statistics
        context['category_distribution'] = papers.exclude(
            broad_subject_term__isnull=True
        ).values('broad_subject_term').annotate(
            count=Count('id'),
            avg_transparency=Avg('transparency_score'),
            data_sharing_pct=Count('id', filter=Q(is_open_data=True)) * 100.0 / Count('id'),
            code_sharing_pct=Count('id', filter=Q(is_open_code=True)) * 100.0 / Count('id'),
            coi_disclosure_pct=Count('id', filter=Q(is_coi_pred=True)) * 100.0 / Count('id'),
            funding_disclosure_pct=Count('id', filter=Q(is_fund_pred=True)) * 100.0 / Count('id'),
            protocol_registration_pct=Count('id', filter=Q(is_register_pred=True)) * 100.0 / Count('id'),
            open_access_pct=Count('id', filter=Q(is_open_access=True)) * 100.0 / Count('id'),
        ).order_by('-count')[:10]  # Top 10 categories
        
        return context

class FieldStatisticsView(DetailView):
    """Statistics for a specific research field"""
    model = ResearchField
    template_name = 'tracker/field_statistics.html'
    context_object_name = 'field'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get papers in this field (simplified - would need better field matching)
        papers = Paper.objects.filter(
            journal__broad_subject_terms__icontains=self.object.name
        )
        
        context['total_papers'] = papers.count()
        context['avg_transparency_score'] = papers.aggregate(
            avg_score=Avg('transparency_score')
        )['avg_score'] or 0
        
        # Field-specific statistics
        context['field_stats'] = {
            'data_sharing': (papers.filter(is_open_data=True).count() / 
                           max(papers.count(), 1)) * 100,
            'code_sharing': (papers.filter(is_open_code=True).count() / 
                           max(papers.count(), 1)) * 100,
            'coi_disclosure': (papers.filter(is_coi_pred=True).count() / 
                             max(papers.count(), 1)) * 100,
        }
        
        return context

# API Views for AJAX/JSON responses
class TransparencyByYearAPI(View):
    """API endpoint for transparency trends by year"""
    
    def get(self, request):
        yearly_data = Paper.objects.values('pub_year').annotate(
            total=Count('id'),
            data_sharing=Count('id', filter=Q(is_open_data=True)),
            code_sharing=Count('id', filter=Q(is_open_code=True)),
            coi_disclosure=Count('id', filter=Q(is_coi_pred=True)),
            avg_transparency=Avg('transparency_score')
        ).order_by('pub_year')
        
        data = list(yearly_data)
        return JsonResponse({'data': data})

class TransparencyByFieldAPI(View):
    """API endpoint for transparency by research field"""
    
    def get(self, request):
        # Simplified field analysis - would need more sophisticated categorization
        field_data = []
        major_fields = ['Dentistry', 'Medicine', 'Surgery', 'Orthodontics']
        
        for field in major_fields:
            papers = Paper.objects.filter(
                journal__broad_subject_terms__icontains=field
            )
            
            if papers.exists():
                field_data.append({
                    'field': field,
                    'total_papers': papers.count(),
                    'avg_transparency': papers.aggregate(
                        avg=Avg('transparency_score')
                    )['avg'] or 0,
                    'data_sharing_pct': (papers.filter(is_open_data=True).count() / 
                                       papers.count()) * 100
                })
        
        return JsonResponse({'data': field_data})

class JournalDistributionAPI(View):
    """API endpoint for journal distribution data"""
    
    def get(self, request):
        distribution = Journal.objects.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:15]
        
        data = list(distribution)
        return JsonResponse({'data': data})

# User Management Views
class SignUpView(View):
    """User registration view"""
    template_name = 'registration/signup.html'
    
    def get(self, request):
        form = UserCreationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('tracker:home')
        return render(request, self.template_name, {'form': form})

class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'tracker/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['profile'] = self.request.user.userprofile
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=self.request.user)
            context['profile'] = self.request.user.userprofile
        return context

class EditProfileView(LoginRequiredMixin, View):
    """Edit user profile"""
    template_name = 'tracker/edit_profile.html'
    
    def get(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        
        form = UserProfileForm(instance=profile)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('tracker:profile')
        return render(request, self.template_name, {'form': form})

# Research Field Views
class ResearchFieldListView(ListView):
    """List of research fields"""
    model = ResearchField
    template_name = 'tracker/field_list.html'
    context_object_name = 'fields'
    
    def get_queryset(self):
        return ResearchField.objects.all().order_by('-total_papers', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate summary statistics
        fields = ResearchField.objects.all()
        context['total_fields'] = fields.count()
        context['max_papers'] = fields.aggregate(max_papers=Max('total_papers'))['max_papers'] or 0
        context['max_journals'] = fields.aggregate(max_journals=Max('total_journals'))['max_journals'] or 0
        context['active_fields'] = fields.filter(total_papers__gt=0).count()
        
        return context

class ResearchFieldDetailView(DetailView):
    """Detail view for research fields"""
    model = ResearchField
    template_name = 'tracker/field_detail.html'
    context_object_name = 'field'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        field = self.object
        
        # Get papers with this broad subject term
        field_papers = Paper.objects.filter(
            broad_subject_term=field.name
        ).select_related('journal')
        
        # Recent papers (last 10, ordered by publication year)
        context['recent_papers'] = field_papers.order_by('-pub_year', '-created_at')[:10]
        
        # Top journals by paper count in this field
        journals_in_field = Journal.objects.filter(
            papers__broad_subject_term=field.name
        ).annotate(
            papers_count=Count('papers', filter=Q(papers__broad_subject_term=field.name)),
            avg_transparency=Avg('papers__transparency_score', filter=Q(papers__broad_subject_term=field.name))
        ).filter(papers_count__gt=0).order_by('-papers_count')[:10]
        
        context['top_journals'] = journals_in_field
        
        # Transparency trends and statistics
        if field_papers.exists():
            total_papers = field_papers.count()
            
            context['transparency_stats'] = {
                'total_papers': total_papers,
                'data_sharing_pct': round((field_papers.filter(is_open_data=True).count() / total_papers) * 100, 1),
                'code_sharing_pct': round((field_papers.filter(is_open_code=True).count() / total_papers) * 100, 1),
                'coi_disclosure_pct': round((field_papers.filter(is_coi_pred=True).count() / total_papers) * 100, 1),
                'funding_disclosure_pct': round((field_papers.filter(is_fund_pred=True).count() / total_papers) * 100, 1),
                'protocol_registration_pct': round((field_papers.filter(is_register_pred=True).count() / total_papers) * 100, 1),
                'open_access_pct': round((field_papers.filter(is_open_access=True).count() / total_papers) * 100, 1),
                'avg_transparency_score': field_papers.aggregate(avg=Avg('transparency_score'))['avg'] or 0,
            }
            
            # Year-wise transparency trends (last 5 years)
            from django.utils import timezone
            current_year = timezone.now().year
            
            yearly_trends = []
            for year in range(current_year - 4, current_year + 1):
                year_papers = field_papers.filter(pub_year=year)
                if year_papers.exists():
                    yearly_trends.append({
                        'year': year,
                        'papers_count': year_papers.count(),
                        'avg_transparency': year_papers.aggregate(avg=Avg('transparency_score'))['avg'] or 0,
                        'data_sharing_pct': round((year_papers.filter(is_open_data=True).count() / year_papers.count()) * 100, 1),
                        'open_access_pct': round((year_papers.filter(is_open_access=True).count() / year_papers.count()) * 100, 1),
                    })
            
            context['yearly_trends'] = yearly_trends
        else:
            context['transparency_stats'] = {
                'total_papers': 0,
                'data_sharing_pct': 0,
                'code_sharing_pct': 0,
                'coi_disclosure_pct': 0,
                'funding_disclosure_pct': 0,
                'protocol_registration_pct': 0,
                'open_access_pct': 0,
                'avg_transparency_score': 0,
            }
            context['yearly_trends'] = []
        
        return context

class TrendsView(TemplateView):
    """Trends analysis page"""
    template_name = 'tracker/trends.html'

class ExportDataView(LoginRequiredMixin, View):
    """Export data as CSV"""
    
    def get(self, request):
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ost_papers.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'PMID', 'Title', 'Authors', 'Journal', 'Year', 'DOI',
            'Data Sharing', 'Code Sharing', 'COI Disclosure', 
            'Funding Disclosure', 'Protocol Registration',
            'Transparency Score'
        ])
        
        # Write data
        papers = Paper.objects.select_related('journal').all()
        for paper in papers:
            writer.writerow([
                paper.pmid, paper.title, paper.author_string,
                paper.journal_title, paper.pub_year, paper.doi,
                paper.is_open_data, paper.is_open_code, paper.is_coi_pred,
                paper.is_fund_pred, paper.is_register_pred,
                paper.transparency_score
            ])
        
        return response

# Admin Views
class ImportDataView(UserPassesTestMixin, TemplateView):
    """Import data from CSV files (admin only)"""
    template_name = 'tracker/import_data.html'
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def post(self, request):
        # Implementation for importing data would go here
        messages.info(request, 'Data import functionality would be implemented here.')
        return redirect('tracker:import_data')

class UpdateTrendsView(UserPassesTestMixin, View):
    """Update transparency trends (admin only)"""
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def post(self, request):
        # Implementation for updating trends would go here
        messages.info(request, 'Trends update functionality would be implemented here.')
        return redirect('tracker:statistics')

class JournalSearchView(TemplateView):
    """Advanced search for journals"""
    template_name = 'tracker/journal_search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = JournalSearchForm()
        context['countries'] = Journal.objects.values_list(
            'country', flat=True
        ).distinct().order_by('country')
        return context


def health_check(request):
    """Health check endpoint for Railway deployment monitoring"""
    try:
        # Simple database connectivity test
        paper_count = Paper.objects.count()
        return JsonResponse({
            'status': 'healthy',
            'papers': paper_count,
            'version': '1.0'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
