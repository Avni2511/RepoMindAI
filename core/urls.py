from django.urls import path
from .views import health_check, ask_ai
from .views import health_check, ask_ai, inspect_repository

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("ask/", ask_ai, name="ask_ai"),
    path("repositories/inspect/", inspect_repository, name="inspect_repository"),
]