from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts.views import AlertIngestView, AlertViewSet, DashboardStatsView

from .jwt_views import PublicTokenObtainPairView, PublicTokenRefreshView

router = DefaultRouter()
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", PublicTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/alerts/ingest/", AlertIngestView.as_view(), name="alert-ingest"),
    path("api/workers/", include("workers.urls")),
    path("api/", include(router.urls)),
]
