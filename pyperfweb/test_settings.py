"""
Test-specific Django settings that suppress verbose output.
"""

# Set testing flag before importing main settings
import os
os.environ['PYPERFWEB_TESTING'] = '1'

from .settings import *

# Minimal logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'ERROR',
    },
    'loggers': {
        'django.request': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'botocore': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'boto3': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}