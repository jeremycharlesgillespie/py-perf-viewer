from django.urls import path, re_path, include
from . import views

app_name = 'dashboard'

urlpatterns = [
    # API endpoints (keep these for the Vue.js app)
    path('api/', include('pyperfweb.dashboard.api_urls')),
    
    # Serve Vue.js SPA for all other routes
    re_path(r'^.*/$', views.spa_view, name='spa'),
    path('', views.spa_view, name='spa_root'),
]