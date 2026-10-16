"""Authentication and permissions for service (device) tokens.

Producers send ``Authorization: Device <key>``. A request authenticated this
way carries a :class:`ServicePrincipal` as ``request.user``. It deliberately
reports ``is_authenticated = False`` and holds no role, so ``IsAuthenticated``
and every role-based permission class refuse it; only the ingest endpoints
that check for a service principal explicitly accept it.
"""

from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.permissions import BasePermission

from .models import ServiceToken

KEYWORD = "Device"


class ServicePrincipal:
    is_authenticated = False
    is_anonymous = False
    is_active = True
    is_staff = False
    is_superuser = False
    pk = None
    id = None

    def __init__(self, token: ServiceToken):
        self.token = token
        self.kind = token.kind
        self.name = token.name

    def has_role_at_least(self, role) -> bool:
        return False

    def __str__(self):
        return f"service:{self.name}"


class ServiceTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].decode().lower() != KEYWORD.lower():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Invalid device authorization header.")
        key = header[1].decode()
        token = (
            ServiceToken.objects.filter(key_hash=ServiceToken.hash_key(key), is_active=True)
            .first()
        )
        if token is None:
            raise exceptions.AuthenticationFailed("Unknown or revoked device token.")
        ServiceToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        return ServicePrincipal(token), token

    def authenticate_header(self, request):
        return KEYWORD


def _is_service(request, kind):
    return isinstance(request.user, ServicePrincipal) and request.user.kind == kind


class IsCameraService(BasePermission):
    message = "This endpoint requires a camera device token."

    def has_permission(self, request, view):
        return _is_service(request, ServiceToken.Kind.CAMERA)


class IsVestGateway(BasePermission):
    message = "This endpoint requires a vest gateway device token."

    def has_permission(self, request, view):
        return _is_service(request, ServiceToken.Kind.VEST_GATEWAY)
