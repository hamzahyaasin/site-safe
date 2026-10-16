import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitesafe.settings")

django_asgi_app = get_asgi_application()

from sitesafe.routing import websocket_urlpatterns  # noqa: E402
from sitesafe.ws_auth import BrowserOriginValidator, JWTQueryAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Browsers may connect only from the dashboard's origins; native apps
        # send no Origin. Either way a valid access token is required
        # (checked again in the consumer).
        "websocket": BrowserOriginValidator(
            JWTQueryAuthMiddleware(URLRouter(websocket_urlpatterns)),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    }
)
