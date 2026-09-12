"""Tests for the User model."""
import pytest
from tests.factories import UserFactory


@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self):
        user = UserFactory()
        assert user.id is not None
        assert user.email
        assert user.name
        assert user.is_active is True
        assert user.is_staff is False

    def test_user_str(self):
        user = UserFactory(name="Jane Doe", email="jane@example.com")
        assert "Jane Doe" in str(user)
        assert "jane@example.com" in str(user)

    def test_user_has_unusable_password(self):
        """Users created via the manager get unusable passwords."""
        from apps.accounts.models import User
        user = User.objects.create_user(email="test@example.com", name="Test")
        assert not user.has_usable_password()

    def test_full_name_property(self):
        user = UserFactory(name="Jane Doe")
        assert user.full_name == "Jane Doe"
