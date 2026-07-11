"""WSGI entry point for Strange Novelty."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strange_novelty.settings.production")

application = get_wsgi_application()
