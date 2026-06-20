"""
ASGI config for cinema_inspection project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')

application = get_asgi_application()
