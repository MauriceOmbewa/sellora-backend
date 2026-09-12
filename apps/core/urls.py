"""
Core app URL patterns — utility endpoints.

POST /api/v1/upload/image/   — Image upload
"""
from django.urls import path
from apps.core.views import ImageUploadView

urlpatterns = [
    path("upload/image/", ImageUploadView.as_view(), name="image-upload"),
]
