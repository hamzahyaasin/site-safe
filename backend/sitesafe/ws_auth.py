"""JWT authentication for websocket connections.

Browsers cannot set an Authorization header on a websocket, so the dashboard
sends its access token in the ``token`` query parameter.
The connection is rejected unless the token is valid and its user active.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
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


class JWTQueryAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        raw = (query.get("token") or [None])[0]
        scope["user"] = await _user_for_token(raw) if raw else AnonymousUser()
        return await super().__call__(scope, receive, send)
