"""
Core app views — shared utility endpoints.

POST /api/v1/upload/image/   — Image upload (authenticated)

Image processing pipeline (Pillow):
  1. Validate raw file MIME type and size (≤ 5 MB raw)
  2. Decode with Pillow — catches corrupt / spoofed files
  3. Enforce aspect ratio: width:height must be between 1:2 and 2:1
  4. Downscale if either dimension exceeds MAX_DIMENSION (2000 px)
     — preserves aspect ratio, never upscales
  5. Re-encode as WebP at quality=85
     — visually lossless for product photos, ~60-80 % smaller than JPEG
  6. Final size guard: reject if WebP output > 2 MB
     (catches pathological high-entropy images that compress poorly)
  7. Save and return the public URL
"""
import io
import os
import uuid
import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import created_response
from common.exceptions import ValidationError

logger = logging.getLogger("apps")

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}

# Raw upload cap — reject obviously oversized files before even opening them
MAX_RAW_BYTES = 5 * 1024 * 1024          # 5 MB

# Maximum pixel dimension on either axis after processing
MAX_DIMENSION = 2000                      # px

# Aspect ratio limits: min W/H = 0.5 (1:2 portrait), max W/H = 2.0 (2:1 landscape)
MIN_ASPECT = 0.5
MAX_ASPECT = 2.0

# Processed output cap — safety net for high-entropy inputs
MAX_OUTPUT_BYTES = 2 * 1024 * 1024       # 2 MB

# WebP encode quality
WEBP_QUALITY = 85


def _process_image(raw_bytes: bytes) -> bytes:
    """
    Open, validate, resize, and re-encode an image as WebP.

    Raises ValidationError with a user-friendly message on any violation.
    Returns the processed WebP bytes.
    """
    # ── Open ──────────────────────────────────────────────────────────────────
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()                        # detects truncated / corrupt files
        img = Image.open(io.BytesIO(raw_bytes))  # re-open after verify()
    except Exception:
        raise ValidationError("The file could not be read as an image. Please try a different file.")

    # ── Convert to RGB(A) — drop palette, EXIF orientation, etc. ─────────────
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    w, h = img.size

    # ── Aspect ratio check ────────────────────────────────────────────────────
    ratio = w / h
    if ratio < MIN_ASPECT or ratio > MAX_ASPECT:
        raise ValidationError(
            f"Image dimensions ({w}×{h} px) are too extreme. "
            f"Please use a roughly square or moderate-landscape image "
            f"(width:height between 1:2 and 2:1)."
        )

    # ── Downscale if too large (never upscale) ────────────────────────────────
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # ── Encode as WebP ────────────────────────────────────────────────────────
    buf = io.BytesIO()
    save_kwargs = {"format": "WEBP", "quality": WEBP_QUALITY, "method": 4}
    # Preserve transparency for RGBA images
    if img.mode == "RGBA":
        save_kwargs["lossless"] = False
    img.save(buf, **save_kwargs)
    webp_bytes = buf.getvalue()

    # ── Final size guard ──────────────────────────────────────────────────────
    if len(webp_bytes) > MAX_OUTPUT_BYTES:
        raise ValidationError(
            f"The processed image is still too large "
            f"({len(webp_bytes) / 1024 / 1024:.1f} MB). "
            f"Please reduce the image resolution or use a simpler image."
        )

    return webp_bytes


class ImageUploadView(APIView):
    """
    POST /api/v1/upload/image/

    Upload a single image file. The image is processed server-side:
      - Decoded and validated by Pillow
      - Aspect ratio enforced (1:2 – 2:1)
      - Downscaled to ≤ 2000 px on either axis
      - Re-encoded as WebP @ quality 85

    Used by: business logos, product images, storefront hero images.

    Request: multipart/form-data
      file   — image file (required)
      folder — subfolder hint: 'products' | 'logos' | 'hero' | 'uploads'

    Response:
      { "success": true, "data": { "url": "https://..." } }
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError("No file provided. Send the image as 'file' in a multipart form.")

        # ── MIME type check (fast, before reading bytes) ──────────────────────
        content_type = file_obj.content_type
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(
                f"Unsupported file type: {content_type}. "
                f"Allowed: JPEG, PNG, WebP, GIF."
            )

        # ── Raw size check ────────────────────────────────────────────────────
        if file_obj.size > MAX_RAW_BYTES:
            raise ValidationError(
                f"File is too large: {file_obj.size / 1024 / 1024:.1f} MB. "
                f"Maximum allowed is 5 MB."
            )

        # ── Process through Pillow ────────────────────────────────────────────
        raw_bytes = file_obj.read()
        webp_bytes = _process_image(raw_bytes)

        # ── Build storage path: {folder}/{uuid}.webp ──────────────────────────
        folder = request.data.get("folder", "uploads").strip("/")
        if not folder or "/" in folder or ".." in folder:
            folder = "uploads"

        filename = f"{folder}/{uuid.uuid4().hex}.webp"
        saved_path = default_storage.save(filename, ContentFile(webp_bytes))
        file_url = default_storage.url(saved_path)

        # Ensure absolute URL in development
        if settings.DEBUG and not file_url.startswith("http"):
            base = request.build_absolute_uri("/")[:-1]
            file_url = f"{base}{file_url}"

        logger.info(
            "Image uploaded by user %s → %s (raw=%d B, webp=%d B, ratio=%.0f%%)",
            request.user.id, saved_path, len(raw_bytes), len(webp_bytes),
            len(webp_bytes) / len(raw_bytes) * 100 if raw_bytes else 0,
        )

        return created_response(data={"url": file_url})
