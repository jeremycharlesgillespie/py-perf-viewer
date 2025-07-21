from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main views
    path('', views.dashboard_home, name='home'),
    path('records/', views.performance_records, name='records'),
    path('records/<str:record_id>/', views.record_detail, name='record_detail'),
    path('functions/<str:function_name>/', views.function_analysis, name='function_analysis'),
    
    # API endpoints
    path('api/metrics/', views.api_metrics, name='api_metrics'),
    path('api/hostnames/', views.api_hostnames, name='api_hostnames'),
    path('api/functions/', views.api_functions, name='api_functions'),
]