import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitesafe.settings")

django_asgi_app = get_asgi_application()

from sitesafe.routing import websocket_urlpatterns  # noqa: E402
from sitesafe.ws_auth import JWTQueryAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Only the dashboard's own origins may open a socket, and only with a
        # valid access token (checked again in the consumer).
        "websocket": OriginValidator(
            JWTQueryAuthMiddleware(URLRouter(websocket_urlpatterns)),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    }
)
