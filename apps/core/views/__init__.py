"""
Core app views — shared utility endpoints.

POST /api/v1/upload/image/   — Image upload (authenticated)
"""
import os
import uuid
import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import created_response
from common.exceptions import ValidationError

logger = logging.getLogger("apps")

# Allowed MIME types for uploaded images
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

# 10 MB max
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


class ImageUploadView(APIView):
    """
    POST /api/v1/upload/image/

    Upload a single image file.
    Returns the public URL of the uploaded image.

    Used by:
      - Business logo upload (onboarding + settings)
      - Product images
      - Storefront hero image

    Request: multipart/form-data
      file — the image file (required)
      folder — optional subfolder hint (e.g. 'products', 'logos', 'hero')
                stored under media/{folder}/{uuid}.{ext}

    Response:
      { "success": true, "data": { "url": "http://..." } }

    Storage:
      Development: local media/ directory (served by Django in DEBUG mode)
      Production:  S3 via django-storages (when USE_S3=True in settings)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError("No file provided. Send the image as 'file' in a multipart form.")

        # Validate MIME type
        content_type = file_obj.content_type
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(
                f"Unsupported file type: {content_type}. "
                f"Allowed: jpeg, png, webp, gif."
            )

        # Validate file size
        if file_obj.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                f"File too large: {file_obj.size / 1024 / 1024:.1f}MB. "
                f"Maximum allowed: 10MB."
            )

        # Build storage path: media/{folder}/{uuid}.{ext}
        folder = request.data.get("folder", "uploads").strip("/")
        if not folder or "/" in folder or ".." in folder:
            folder = "uploads"

        ext = os.path.splitext(file_obj.name)[1].lower() or ".jpg"
        filename = f"{folder}/{uuid.uuid4().hex}{ext}"

        # Save to storage (local or S3 depending on settings)
        saved_path = default_storage.save(filename, ContentFile(file_obj.read()))
        file_url = default_storage.url(saved_path)

        # Ensure absolute URL in development
        if settings.DEBUG and not file_url.startswith("http"):
            base = request.build_absolute_uri("/")[:-1]
            file_url = f"{base}{file_url}"

        logger.info(
            "Image uploaded by user %s → %s (%d bytes)",
            request.user.id, saved_path, file_obj.size,
        )

        return created_response(data={"url": file_url})
