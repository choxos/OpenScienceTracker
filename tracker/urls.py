from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Home and dashboard
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Papers
    path('papers/', views.PaperListView.as_view(), name='paper_list'),
    path('papers/<str:pmid>/', views.PaperDetailView.as_view(), name='paper_detail'),
    path('papers/search/', views.PaperSearchView.as_view(), name='paper_search'),
    
    # Journals
    path('journals/', views.JournalListView.as_view(), name='journal_list'),
    path('journals/<int:pk>/', views.JournalDetailView.as_view(), name='journal_detail'),
    path('journals/search/', views.JournalSearchView.as_view(), name='journal_search'),
    
    # Statistics and analytics
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('statistics/field/<int:field_id>/', views.FieldStatisticsView.as_view(), name='field_statistics'),
    path('statistics/trends/', views.TrendsView.as_view(), name='trends'),
    path('statistics/export/', views.ExportDataView.as_view(), name='export_data'),
    
    # API endpoints for charts
    path('api/transparency-by-year/', views.TransparencyByYearAPI.as_view(), name='api_transparency_by_year'),
    path('api/transparency-by-field/', views.TransparencyByFieldAPI.as_view(), name='api_transparency_by_field'),
    path('api/journal-distribution/', views.JournalDistributionAPI.as_view(), name='api_journal_distribution'),
    
    # User management
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.EditProfileView.as_view(), name='edit_profile'),
    
    # Fields and research areas
    path('fields/', views.ResearchFieldListView.as_view(), name='field_list'),
    path('fields/<int:pk>/', views.ResearchFieldDetailView.as_view(), name='field_detail'),
    
    # Data management (admin only)
    path('admin/import-data/', views.ImportDataView.as_view(), name='import_data'),
    path('admin/update-trends/', views.UpdateTrendsView.as_view(), name='update_trends'),
] 