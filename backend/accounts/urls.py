from django.urls import path

from .views import FCMTokenDeactivateView, FCMTokenRegisterView

urlpatterns = [
    path("", FCMTokenRegisterView.as_view(), name="fcm-token-register"),
    path("<path:token>/", FCMTokenDeactivateView.as_view(), name="fcm-token-deactivate"),
]
