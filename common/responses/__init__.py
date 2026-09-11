"""
Standardized API response helpers.

All successful responses follow this envelope:
    {
        "success": true,
        "data": { ... }        ← single object
    }
or:
    {
        "success": true,
        "message": "Done."     ← action confirmation
    }
"""
from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """Return a successful data response."""
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    return Response(payload, status=status_code)


def created_response(data, message=None):
    """Return a 201 Created response."""
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def no_content_response():
    """Return a 204 No Content response."""
    return Response(status=status.HTTP_204_NO_CONTENT)
