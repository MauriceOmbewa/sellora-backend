"""
Account views — HTTP request/response layer for the accounts domain.

Views are intentionally thin:
  1. Validate/read inputs
  2. Call a service or selector
  3. Return a response or redirect

No business logic, no ORM queries, no token generation lives here.

─── Google OAuth flow ────────────────────────────────────────────────────────

  1. Frontend opens:
         GET /api/v1/auth/google/?next=web      (website)
         GET /api/v1/auth/google/?next=app      (mobile app)

  2. Backend builds the Google authorization URL (with `next` encoded in
     Google's `state` param) and redirects the browser to Google.

  3. User logs in on Google's page.

  4. Google redirects back to:
         GET /api/v1/auth/google/callback/?code=...&state=web

  5. Backend exchanges the code for user info, issues JWT tokens, then
     redirects the user to the correct destination:
         web → https://yourfrontend.com/auth/callback?access=...&refresh=...
         app → sellora://auth/callback?access=...&refresh=...

"""
import logging
import urllib.parse

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import UserSerializer
from apps.accounts.serializers.token import get_tokens_for_user
from apps.accounts.services import authenticate_with_google_code, build_google_auth_url
from common.responses import no_content_response, success_response

logger = logging.getLogger("apps")

# Valid origins the `next` param may carry.
# Anything outside this set is treated as "web" to prevent open redirect abuse.
VALID_ORIGINS = {"web", "app"}


class GoogleInitiateView(APIView):
    """
    GET /api/v1/auth/google/?next=web
    GET /api/v1/auth/google/?next=app

    Step 1 of the OAuth flow. The frontend simply navigates the user's
    browser to this URL — no JavaScript SDK, no client ID needed on the
    frontend side.

    Query params:
        next (optional): "web" (default) or "app"
                         Tells the backend where to redirect after login.

    Response:
        302 redirect → Google's login/consent page
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Read the origin. Default to "web" and sanitize against the allowlist
        # so a crafted ?next=https://evil.com can never become a redirect target.
        origin = request.query_params.get("next", "web").lower()
        if origin not in VALID_ORIGINS:
            origin = "web"

        # The origin is encoded into Google's `state` param.
        # Google passes it back unchanged in the callback — no server-side
        # state storage needed.
        google_url = build_google_auth_url(state=origin)

        return HttpResponseRedirect(google_url)


class GoogleCallbackView(APIView):
    """
    GET /api/v1/auth/google/callback/?code=...&state=...

    Step 2 of the OAuth flow. Google redirects here after the user
    authenticates. This view:
      1. Checks for errors from Google (user cancelled, etc.)
      2. Exchanges the authorization code for the user's profile
      3. Gets or creates the local user record
      4. Issues JWT tokens
      5. Redirects the user to the correct destination based on `state`

    On success:
        web → 302 to {FRONTEND_WEB_URL}/auth/callback?access=...&refresh=...
        app → 302 to {APP_DEEP_LINK_SCHEME}://auth/callback?access=...&refresh=...

    On error:
        web → 302 to {FRONTEND_WEB_URL}/auth/error?message=...
        app → 302 to {APP_DEEP_LINK_SCHEME}://auth/error?message=...
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # ── Read params from Google ───────────────────────────────────────────
        error = request.query_params.get("error")
        code = request.query_params.get("code")
        state = request.query_params.get("state", "web").lower()

        # Sanitize state — never trust values you didn't put there
        if state not in VALID_ORIGINS:
            state = "web"

        # ── Handle user-cancelled or Google error ─────────────────────────────
        if error:
            logger.warning("Google OAuth error returned: %s", error)
            return self._redirect_error(state, "Google sign-in was cancelled or failed.")

        if not code:
            return self._redirect_error(state, "No authorization code received from Google.")

        # ── Exchange code → user, issue tokens ───────────────────────────────
        try:
            user, created = authenticate_with_google_code(code)
        except AuthenticationFailed as exc:
            logger.warning("Google OAuth authentication failed: %s", exc)
            return self._redirect_error(state, str(exc.detail))
        except Exception as exc:
            logger.exception("Unexpected error during Google OAuth callback: %s", exc)
            return self._redirect_error(state, "An unexpected error occurred. Please try again.")

        # ── Issue JWT tokens ──────────────────────────────────────────────────
        tokens = get_tokens_for_user(user)

        # ── Redirect to the right place ───────────────────────────────────────
        return self._redirect_success(state, tokens)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _redirect_success(self, origin: str, tokens: dict) -> HttpResponseRedirect:
        """
        Build the success redirect URL and send the user there.

        Tokens are passed as query parameters so the web app / mobile app
        can read them from the URL on landing.

        Web:  https://yourfrontend.com/auth/callback?access=TOKEN&refresh=TOKEN
        App:  sellora://auth/callback?access=TOKEN&refresh=TOKEN
        """
        params = urllib.parse.urlencode({
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        })

        if origin == "app":
            # Deep link — the mobile app must register this URI scheme
            url = f"{settings.APP_DEEP_LINK_SCHEME}://auth/callback?{params}"
        else:
            # Standard web redirect
            url = f"{settings.FRONTEND_WEB_URL}/auth/callback?{params}"

        return HttpResponseRedirect(url)

    def _redirect_error(self, origin: str, message: str) -> HttpResponseRedirect:
        """
        Redirect to the error page for the correct origin with a message.

        Web:  https://yourfrontend.com/auth/error?message=...
        App:  sellora://auth/error?message=...
        """
        params = urllib.parse.urlencode({"message": message})

        if origin == "app":
            url = f"{settings.APP_DEEP_LINK_SCHEME}://auth/error?{params}"
        else:
            url = f"{settings.FRONTEND_WEB_URL}/auth/error?{params}"

        return HttpResponseRedirect(url)


class MeView(APIView):
    """
    GET /api/v1/auth/me/

    Return the profile of the currently authenticated user.
    Requires a valid Bearer JWT in the Authorization header.

    Response:
        {
            "success": true,
            "data": { "id": ..., "email": ..., "name": ..., "avatar": ... }
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # request.user is populated by JWTAuthentication from the Bearer token
        serializer = UserSerializer(request.user)
        return success_response(data=serializer.data)


class SignOutView(APIView):
    """
    POST /api/v1/auth/signout/

    Blacklist the refresh token so it can no longer be used.
    The access token remains valid until it naturally expires (short-lived).

    Request body:
        { "refresh": "<refresh_token>" }

    Response: 204 No Content
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                # Already blacklisted or invalid — treat as already signed out
                pass
        return no_content_response()
