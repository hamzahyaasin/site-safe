from django.urls import path

from alerts.consumers import DashboardConsumer

websocket_urlpatterns = [
    path("ws/dashboard/default/", DashboardConsumer.as_asgi()),
]
