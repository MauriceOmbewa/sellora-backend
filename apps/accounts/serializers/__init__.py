"""
Account serializers — output shaping for the accounts domain.

In the backend-initiated OAuth flow the frontend never sends us a token
or any auth payload — the browser is redirected straight to Google and
back. So there is no input to validate here.

The only serializer needed is UserSerializer, which shapes the user object
for the /me/ endpoint response.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only representation of a user.

    Used by:
      - GET /api/v1/auth/me/  → returns the current user's profile
    """
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "avatar",
            "is_staff",
            "created_at",
        ]
        read_only_fields = fields
