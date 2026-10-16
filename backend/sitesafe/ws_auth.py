"""JWT authentication for websocket connections.

Browsers cannot set an Authorization header on a websocket, so the dashboard
sends its access token in the ``token`` query parameter.
The connection is rejected unless the token is valid and its user active.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.security.websocket import OriginValidator
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_for_token(raw_token):
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    from accounts.models import User

    try:
        token = AccessToken(raw_token)
    except TokenError:
        return AnonymousUser()
    user = User.objects.filter(pk=token.get("user_id"), is_active=True).first()
    return user or AnonymousUser()


class BrowserOriginValidator(OriginValidator):
    """Reject sockets opened by pages on other sites; allow native apps.

    The Origin check exists to stop a malicious web page from opening a
    socket with a victim's browser. Browsers always send Origin; the mobile
    app (a native client) sends none, and cannot be driven by another site,
    so a missing Origin is allowed. Every socket still needs a valid JWT.
    """

    def valid_origin(self, parsed_origin):
        if parsed_origin is None:
            return True
        return super().valid_origin(parsed_origin)


class JWTQueryAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        raw = (query.get("token") or [None])[0]
        scope["user"] = await _user_for_token(raw) if raw else AnonymousUser()
        return await super().__call__(scope, receive, send)
