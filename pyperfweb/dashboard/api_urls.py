from django.urls import path
from . import views

# API-only URL patterns
app_name = 'api'

urlpatterns = [
    # Performance API endpoints
    path('metrics/', views.api_metrics, name='metrics'),
    path('hostnames/', views.api_hostnames, name='hostnames'),
    path('functions/', views.api_functions, name='functions'),
    path('timeline/', views.api_timeline_data, name='timeline_data'),
    
    # System API endpoints
    path('system/', views.api_system_metrics, name='system_metrics'),
    path('system/hostnames/', views.api_system_hostnames, name='system_hostnames'),
]