"""
ASGI config for Sellora backend.

Exposes the ASGI callable as a module-level variable named `application`.
Ready for WebSocket support when needed (e.g. real-time order notifications).
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()
