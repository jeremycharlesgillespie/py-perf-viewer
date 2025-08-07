"""
Constants for py-perf-viewer dashboard.
Central location for configuration values to reduce code duplication.
"""

# Time thresholds (in seconds)
ONLINE_THRESHOLD_SECONDS = 360  # 6 minutes - system considered offline if no update
CACHE_TTL_DASHBOARD = 300  # 5 minutes - dashboard cache TTL
CACHE_TTL_HOST_METRICS = 180  # 3 minutes - host metrics cache TTL

# DynamoDB settings
DYNAMODB_TABLE_NAME = 'py-perf-system'
DYNAMODB_SCAN_SEGMENTS = 8  # Number of parallel segments for scanning
DYNAMODB_SCAN_LIMIT = 300  # Records per scan

# Frontend polling intervals (in milliseconds)
FRONTEND_POLL_INTERVAL_MS = 120000  # 2 minutes

# Data limits
MAX_TIMELINE_POINTS = 200  # Maximum data points for charts
MAX_DASHBOARD_HOSTS = 100  # Maximum hosts to show on dashboard

# Daemon settings (for reference)
DAEMON_UPLOAD_INTERVAL_SECONDS = 60  # How often daemon uploads
DAEMON_SAMPLE_INTERVAL_SECONDS = 1.0  # How often daemon samples metrics