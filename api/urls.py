"""
Root API URL dispatcher.
Supports versioning — add v2/ here when needed.
"""
from django.urls import path, include

urlpatterns = [
    path("v1/", include("api.v1.urls")),
]
