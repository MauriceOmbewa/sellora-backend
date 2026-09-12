"""Tests for business API endpoints."""
import pytest
from django.urls import reverse
from tests.factories import BusinessFactory, UserFactory


@pytest.mark.django_db
class TestBusinessListCreateView:

    def test_list_requires_auth(self, api_client):
        response = api_client.get("/api/v1/businesses/")
        assert response.status_code == 401

    def test_list_returns_own_businesses(self, auth_client, user):
        # Create 2 businesses for our user
        BusinessFactory(owner=user)
        BusinessFactory(owner=user)
        # Create 1 for another user — should not appear
        BusinessFactory()

        response = auth_client.get("/api/v1/businesses/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_create_business(self, auth_client):
        payload = {
            "name": "My Test Store",
            "category": "cosmetics",
            "description": "A test store",
        }
        response = auth_client.post("/api/v1/businesses/", payload, format="json")
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "My Test Store"
        assert data["data"]["slug"] == "my-test-store"
        assert data["data"]["plan"] == "starter"

    def test_create_business_requires_name(self, auth_client):
        response = auth_client.post("/api/v1/businesses/", {"category": "other"}, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestBusinessDetailView:

    def test_get_business(self, auth_client, user, business):
        response = auth_client.get(f"/api/v1/businesses/{business.id}/")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(business.id)

    def test_cannot_access_other_users_business(self, auth_client):
        other_biz = BusinessFactory()  # different owner
        response = auth_client.get(f"/api/v1/businesses/{other_biz.id}/")
        assert response.status_code == 403

    def test_patch_business(self, auth_client, business):
        response = auth_client.patch(
            f"/api/v1/businesses/{business.id}/",
            {"description": "Updated description"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["description"] == "Updated description"
