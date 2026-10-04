"""
ASGI config for Sellora backend.

Exposes the ASGI callable as a module-level variable named `application`.
Supports both HTTP requests and WebSocket connections.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)


django_asgi_app = get_asgi_application()


from apps.messages.routing import websocket_urlpatterns


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(
            websocket_urlpatterns,
        ),
    }
)
