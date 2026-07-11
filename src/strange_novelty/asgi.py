"""ASGI entry point for Strange Novelty."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strange_novelty.settings.production")

application = get_asgi_application()
