"""Tests for Business, BusinessSettings, StorefrontSettings models."""
import pytest
from tests.factories import BusinessFactory, BusinessSettingsFactory, StorefrontSettingsFactory


@pytest.mark.django_db
class TestBusinessModel:

    def test_create_business(self):
        biz = BusinessFactory()
        assert biz.id is not None
        assert biz.name
        assert biz.slug
        assert biz.status == "active"
        assert biz.plan == "starter"

    def test_business_str(self):
        biz = BusinessFactory(name="Test Shop", slug="test-shop")
        assert "Test Shop" in str(biz)
        assert "test-shop" in str(biz)

    def test_default_json_fields_populated(self):
        biz = BusinessFactory()
        biz.refresh_from_db()
        assert isinstance(biz.theme, dict)
        assert "primaryColor" in biz.theme
        assert isinstance(biz.contact, dict)
        assert "country" in biz.contact

    def test_signal_creates_companion_records(self):
        """Signal should auto-create BusinessSettings + StorefrontSettings."""
        from apps.businesses.models import BusinessSettings, StorefrontSettings
        biz = BusinessFactory()
        assert BusinessSettings.objects.filter(business=biz).exists()
        assert StorefrontSettings.objects.filter(business=biz).exists()


@pytest.mark.django_db
class TestBusinessService:

    def test_create_business_generates_slug(self):
        from apps.businesses.services import create_business
        from tests.factories import UserFactory
        user = UserFactory()
        biz = create_business(user, name="Maison Aura", category="cosmetics")
        assert biz.slug == "maison-aura"

    def test_create_business_deduplicates_slug(self):
        from apps.businesses.services import create_business
        from tests.factories import UserFactory
        user = UserFactory()
        biz1 = create_business(user, name="Test Shop", category="other")
        biz2 = create_business(user, name="Test Shop", category="other")
        assert biz1.slug != biz2.slug
        assert biz2.slug == "test-shop-2"
