"""
API URL Configuration for Open Science Tracker

This module defines the URL patterns for the REST API endpoints,
including versioning, viewsets, and documentation.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularRedocView, 
    SpectacularSwaggerView
)

from .api_views import (
    PaperViewSet,
    JournalViewSet, 
    ResearchFieldViewSet,
    APIOverviewView
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'papers', PaperViewSet, basename='paper')
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'research-fields', ResearchFieldViewSet, basename='researchfield')

app_name = 'api'

urlpatterns = [
    # API Overview
    path('', APIOverviewView.as_view(), name='api-overview'),
    
    # API endpoints
    path('v1/', include(router.urls)),
    
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
    
    # API Authentication (if needed in future)
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]

# Additional URL patterns for custom endpoints can be added here 