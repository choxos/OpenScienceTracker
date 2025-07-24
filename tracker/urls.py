from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Main views
    path('', views.HomeView.as_view(), name='home'),
    path('papers/', views.PaperListView.as_view(), name='paper_list'),
    path('papers/<str:epmc_id>/', views.PaperDetailView.as_view(), name='paper_detail'),
    path('journals/', views.JournalListView.as_view(), name='journal_list'),
    path('journals/<int:pk>/', views.JournalDetailView.as_view(), name='journal_detail'),
    path('fields/', views.FieldListView.as_view(), name='field_list'),
    path('fields/<int:pk>/', views.FieldDetailView.as_view(), name='field_detail'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('about/', views.AboutView.as_view(), name='about'),
    
    # Ajax endpoints for partial content loading
    path('ajax/', views.HomeView.as_view(template_name='tracker/partials/home_content.html'), name='ajax_home'),
    path('ajax/papers/', views.PaperListView.as_view(template_name='tracker/partials/paper_list_content.html'), name='ajax_paper_list'),
    path('ajax/papers/<str:epmc_id>/', views.PaperDetailView.as_view(template_name='tracker/partials/paper_detail_content.html'), name='ajax_paper_detail'),
    path('ajax/journals/', views.JournalListView.as_view(template_name='tracker/partials/journal_list_content.html'), name='ajax_journal_list'),
    path('ajax/journals/<int:pk>/', views.JournalDetailView.as_view(template_name='tracker/partials/journal_detail_content.html'), name='ajax_journal_detail'),
    path('ajax/fields/', views.FieldListView.as_view(template_name='tracker/partials/field_list_content.html'), name='ajax_field_list'),
    path('ajax/fields/<int:pk>/', views.FieldDetailView.as_view(template_name='tracker/partials/field_detail_content.html'), name='ajax_field_detail'),
    path('ajax/statistics/', views.StatisticsView.as_view(template_name='tracker/partials/statistics_content.html'), name='ajax_statistics'),
    path('ajax/about/', views.AboutView.as_view(template_name='tracker/partials/about_content.html'), name='ajax_about'),
] 