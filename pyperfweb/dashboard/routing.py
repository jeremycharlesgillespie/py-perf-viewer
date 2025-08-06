"""
WebSocket URL routing for real-time dashboard updates.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/system/(?P<hostname>[\w.-]+)/$', consumers.SystemDetailConsumer.as_asgi()),
]