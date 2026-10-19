from django.urls import path
from .views import health_check, ask_ai

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("ask/", ask_ai, name="ask_ai"),
]