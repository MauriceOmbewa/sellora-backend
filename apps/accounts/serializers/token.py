"""
Custom JWT token serializer stub.
Full implementation lives in Step 6 (accounts app).
This stub satisfies the SIMPLE_JWT settings reference at startup.
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    """
    Extended to include user info in the token response.
    Populated in Step 6.
    """
    pass
