"""JWT token views explicitly allow unauthenticated access."""

from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class PublicTokenObtainPairView(TokenObtainPairView):
    authentication_classes = []
    permission_classes = [AllowAny]


class PublicTokenRefreshView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]
