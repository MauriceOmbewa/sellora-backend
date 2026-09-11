"""
Authentication middleware placeholder.

JWT authentication is handled by DRF's JWTAuthentication class configured in
REST_FRAMEWORK settings. This file is kept for any future request-level auth
processing that needs to happen before DRF's authentication layer.
"""


class AuthenticationMiddleware:
    """Pass-through — JWT auth is handled by DRF per-view, not globally."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
