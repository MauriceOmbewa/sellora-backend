"""
Root pytest configuration and shared fixtures.

All tests use:
  - In-memory SQLite (config.settings.testing)
  - factory_boy factories for model creation
  - APIClient for endpoint testing
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """Authenticated DRF test client with JWT token."""
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def user(db):
    """Create and return a test user."""
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def business(db, user):
    """Create and return a test business owned by the test user."""
    from tests.factories import BusinessFactory
    return BusinessFactory(owner=user)


@pytest.fixture
def business_client(user, business):
    """Authenticated client with a business context."""
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client
