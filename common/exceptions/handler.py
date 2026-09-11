"""
Global DRF exception handler.

Every API error — whether from DRF, Django, or our custom exceptions —
is normalized into a consistent envelope:

    {
        "success": false,
        "error": {
            "code": "not_found",
            "message": "Business not found.",
            "details": { ... }   ← optional, for validation errors
        }
    }
"""
import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """Convert all exceptions to the standard error envelope."""

    # Map Django exceptions to DRF equivalents
    if isinstance(exc, Http404):
        exc = APIException(detail="Not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDenied):
        exc = APIException(detail="Permission denied.")
        exc.status_code = status.HTTP_403_FORBIDDEN

    # Let DRF do its default handling first (sets response for known types)
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log it and return 500
        logger.exception("Unhandled exception: %s", exc, exc_info=exc)
        return Response(
            {
                "success": False,
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Build normalized error payload
    error_code = getattr(exc, "default_code", "error")
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            error_code = codes
        elif isinstance(codes, dict) and "non_field_errors" in codes:
            error_code = codes["non_field_errors"][0] if codes["non_field_errors"] else error_code

    error_payload = {
        "code": error_code,
        "message": _flatten_message(exc.detail),
    }

    # Include field-level details for validation errors
    if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
        error_payload["details"] = exc.detail

    response.data = {
        "success": False,
        "error": error_payload,
    }

    return response


def _flatten_message(detail):
    """Convert DRF's nested error detail into a single string."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return str(detail[0]) if detail else "An error occurred."
    if isinstance(detail, dict):
        # Return first field's first message
        for key, value in detail.items():
            if key == "non_field_errors":
                return _flatten_message(value)
            return f"{key}: {_flatten_message(value)}"
    return str(detail)
