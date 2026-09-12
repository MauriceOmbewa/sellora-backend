"""
Custom JWT token serializer.

Extends SimpleJWT's default token pair serializer to embed basic user
info directly in the token response, so the frontend doesn't need to
make a separate /me/ call right after login.

Response shape:
    {
        "access": "<jwt_access_token>",
        "refresh": "<jwt_refresh_token>",
        "user": {
            "id": "...",
            "email": "...",
            "name": "...",
            "avatar": "..."
        }
    }
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    """
    Adds a 'user' block to the standard access+refresh response.
    Referenced by SIMPLE_JWT["TOKEN_OBTAIN_SERIALIZER"] in settings.
    """

    @classmethod
    def get_token(cls, user):
        """Embed lightweight claims into the JWT payload itself."""
        token = super().get_token(user)
        # These claims are readable without a DB hit on the frontend
        token["email"] = user.email
        token["name"] = user.name
        return token


def get_tokens_for_user(user) -> dict:
    """
    Generate a JWT access + refresh token pair for any User instance.

    Called by the Google SSO view after authentication — bypasses the
    standard username/password obtain flow entirely.

    Returns:
        {
            "access": "<token>",
            "refresh": "<token>"
        }
    """
    refresh = RefreshToken.for_user(user)

    # Embed the same custom claims we add in CustomTokenObtainSerializer
    refresh["email"] = user.email
    refresh["name"] = user.name

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
