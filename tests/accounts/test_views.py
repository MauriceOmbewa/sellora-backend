"""Tests for auth endpoints."""
import pytest
from django.urls import reverse
from tests.factories import UserFactory


@pytest.mark.django_db
class TestMeView:

    def test_me_requires_auth(self, api_client):
        url = reverse("auth-me")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_me_returns_user_data(self, auth_client, user):
        url = reverse("auth-me")
        response = auth_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == user.email
        assert data["data"]["name"] == user.name
        assert "cost_price" not in str(data)  # private field never leaks


@pytest.mark.django_db
class TestSignOutView:

    def test_signout_requires_auth(self, api_client):
        url = reverse("auth-signout")
        response = api_client.post(url, {})
        assert response.status_code == 401

    def test_signout_returns_204(self, auth_client):
        from rest_framework_simplejwt.tokens import RefreshToken
        from tests.factories import UserFactory
        user = UserFactory()
        from rest_framework.test import APIClient
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        url = reverse("auth-signout")
        response = client.post(url, {"refresh": str(refresh)}, format="json")
        assert response.status_code == 204
