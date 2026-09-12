"""
Accounts URL patterns.

Mounted at /api/v1/auth/ via api/v1/urls.py:
    path("auth/", include("apps.accounts.urls"))

Full paths:
    GET    /api/v1/auth/google/              Initiate Google OAuth — redirects browser to Google
    GET    /api/v1/auth/google/callback/     Google redirects here after login — issues JWT, redirects to frontend/app
    GET    /api/v1/auth/me/                  Current user profile (requires Bearer token)
    POST   /api/v1/auth/signout/             Blacklist refresh token
    POST   /api/v1/auth/token/refresh/       Refresh an access token (SimpleJWT built-in)

─── Important: GOOGLE_REDIRECT_URI in settings (and in Google Cloud Console) ───
The callback URL registered in Google Cloud Console must match GOOGLE_REDIRECT_URI
in your .env exactly, including the trailing slash:

    http://localhost:8000/api/v1/auth/google/callback/       ← development
    https://api.yourdomain.com/api/v1/auth/google/callback/  ← production
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import GoogleCallbackView, GoogleInitiateView, MeView, SignOutView

urlpatterns = [
    # ── Google OAuth ──────────────────────────────────────────────────────────
    # Step 1: frontend navigates user here with ?next=web or ?next=app
    path("google/", GoogleInitiateView.as_view(), name="auth-google-initiate"),
    # Step 2: Google redirects back here with ?code=...&state=...
    path("google/callback/", GoogleCallbackView.as_view(), name="auth-google-callback"),

    # ── Authenticated endpoints ───────────────────────────────────────────────
    path("me/", MeView.as_view(), name="auth-me"),
    path("signout/", SignOutView.as_view(), name="auth-signout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
