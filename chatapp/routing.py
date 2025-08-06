from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/notification/<str:room_name>/<str:user>/', ChatConsumer.as_asgi()),
]