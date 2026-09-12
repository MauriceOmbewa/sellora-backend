"""
Account selectors — read-only queries for the accounts domain.

Selectors are the only place allowed to query the database for reads.
Views and services import from here instead of writing ORM queries inline.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_by_google_id(google_id: str):
    """
    Return the User with this Google sub claim, or None if not found.
    Called during login to check if this Google account already exists.
    """
    return User.objects.filter(google_id=google_id).first()


def get_user_by_email(email: str):
    """
    Return the User with this email, or None if not found.
    Used as a fallback — if a user signed up before and we have their email
    but google_id isn't set yet, we can link the account.
    """
    return User.objects.filter(email=email).first()


def get_user_by_id(user_id):
    """
    Return the User with this UUID primary key, or None.
    Used by the /me/ endpoint.
    """
    return User.objects.filter(id=user_id).first()
