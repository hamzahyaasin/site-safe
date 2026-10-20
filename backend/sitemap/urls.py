from rest_framework.routers import DefaultRouter

from .views import HotWorkPermitViewSet, ZoneViewSet

router = DefaultRouter()
router.register(r"", ZoneViewSet, basename="zone")

urlpatterns = router.urls

permit_router = DefaultRouter()
permit_router.register(r"", HotWorkPermitViewSet, basename="hot-work-permit")
permit_urlpatterns = permit_router.urls
