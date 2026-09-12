"""
Account services — write operations and business logic for the accounts domain.

Services are the only place allowed to create, update, or delete data.
The view calls a service; the service calls selectors and models.
"""
import urllib.parse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.selectors import get_user_by_email, get_user_by_google_id

User = get_user_model()

# ─── Google OAuth endpoints ───────────────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Scopes we request from Google:
#   openid  → lets Google issue an ID token (standard OIDC)
#   email   → user's email address
#   profile → name and avatar picture
GOOGLE_SCOPES = "openid email profile"


def build_google_auth_url(state: str) -> str:
    """
    Build the Google OAuth authorization URL that the backend redirects
    the user to.

    The `state` parameter is Google's CSRF / round-trip carrier.
    We encode the caller's origin (web/app) into it so the callback
    knows where to send the user after login — no session or DB needed.

    Google will pass `state` back unchanged in the callback URL.

    Args:
        state: A string like "web" or "app". The callback reads this back.

    Returns:
        Full Google authorization URL to redirect the user to.
    """
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",       # we want an authorization code, not a token
        "scope": GOOGLE_SCOPES,
        "state": state,                # carried back to us in the callback
        "access_type": "online",       # no refresh tokens needed — JWT handles that
        "prompt": "select_account",    # always show account picker so user can switch accounts
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_user_info(code: str) -> dict:
    """
    Exchange a Google authorization code for user info.

    Two HTTP calls to Google:
      1. POST to token endpoint → get access_token
      2. GET to userinfo endpoint → get email, name, avatar, sub (google_id)

    This is where GOOGLE_CLIENT_SECRET is used — it never leaves the backend.

    Args:
        code: The one-time authorization code from Google's callback.

    Returns:
        Dict with keys: sub, email, name, picture

    Raises:
        AuthenticationFailed on any Google error.
    """
    # ── Step 1: exchange code for access token ────────────────────────────────
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    if not token_response.ok:
        raise AuthenticationFailed(
            f"Failed to exchange Google authorization code: {token_response.text}"
        )

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise AuthenticationFailed("Google did not return an access token.")

    # ── Step 2: fetch user info using the access token ────────────────────────
    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    if not userinfo_response.ok:
        raise AuthenticationFailed(
            f"Failed to fetch Google user info: {userinfo_response.text}"
        )

    return userinfo_response.json()
    # Returns something like:
    # {
    #   "sub": "1234567890",         ← Google's unique user ID
    #   "email": "user@gmail.com",
    #   "name": "John Doe",
    #   "picture": "https://..."
    # }


def get_or_create_user_from_google(google_payload: dict) -> tuple:
    """
    Given Google user info, return (user, created).

    Lookup strategy:
      1. By google_id (sub) — the fast path for returning users.
      2. By email — links an existing account if they logged in another way before.
      3. Neither found — create a new user.

    In cases 2 and 3 we always write google_id onto the user record so
    future logins always hit case 1.

    Args:
        google_payload: The dict returned by exchange_code_for_user_info()

    Returns:
        (user, created) — created is True only for brand new accounts.
    """
    google_id = google_payload["sub"]
    email = google_payload["email"]
    name = google_payload.get("name", "")
    avatar = google_payload.get("picture", "")

    # ── Case 1: returning user ────────────────────────────────────────────────
    user = get_user_by_google_id(google_id)
    if user:
        # Keep avatar in sync in case the user updated their Google profile pic
        if avatar and user.avatar != avatar:
            user.avatar = avatar
            user.save(update_fields=["avatar", "updated_at"])
        return user, False

    # ── Case 2: existing account with same email (link it) ────────────────────
    user = get_user_by_email(email)
    if user:
        user.google_id = google_id
        user.avatar = avatar or user.avatar
        user.save(update_fields=["google_id", "avatar", "updated_at"])
        return user, False

    # ── Case 3: brand new user ────────────────────────────────────────────────
    user = User.objects.create_user(
        email=email,
        name=name,
        google_id=google_id,
        avatar=avatar,
    )
    return user, True


def authenticate_with_google_code(code: str) -> tuple:
    """
    Full Google OAuth flow from authorization code to (user, created).

    Called by the callback view after Google redirects back to us.

    Steps:
      1. Exchange the code for Google user info (two HTTP calls to Google)
      2. Get or create the local user record
      3. Verify the account is active

    The view handles JWT issuance and the final redirect — not here.

    Args:
        code: The authorization code from Google's callback query string.

    Returns:
        (user, created)

    Raises:
        AuthenticationFailed if anything goes wrong.
    """
    google_payload = exchange_code_for_user_info(code)
    user, created = get_or_create_user_from_google(google_payload)

    if not user.is_active:
        raise AuthenticationFailed("This account has been deactivated.")

    return user, created
