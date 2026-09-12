"""
Business selectors — all read/query logic for the businesses domain.

Views and services import from here. No ORM queries elsewhere.
"""
from django.db.models import QuerySet

from apps.businesses.models import Business, BusinessSettings, StorefrontSettings


def get_business_by_id(business_id) -> Business | None:
    """
    Return a Business by its UUID primary key, or None.
    Prefetches related settings to avoid N+1 in detail views.
    """
    try:
        return (
            Business.objects
            .select_related("owner", "settings", "storefront_settings")
            .get(id=business_id)
        )
    except Business.DoesNotExist:
        return None


def get_business_by_slug(slug: str) -> Business | None:
    """
    Return an active, published Business by its public slug, or None.
    Used by the public storefront API — only returns published businesses.
    """
    try:
        return (
            Business.objects
            .select_related("storefront_settings")
            .get(slug=slug, status="active")
        )
    except Business.DoesNotExist:
        return None


def get_user_businesses(user) -> QuerySet:
    """
    Return all businesses owned by a user, ordered by creation date.
    Used on the /businesses/ list endpoint and the business selector screen.
    """
    return (
        Business.objects
        .filter(owner=user)
        .select_related("settings", "storefront_settings")
        .order_by("-created_at")
    )


def get_business_settings(business) -> BusinessSettings | None:
    """Return the BusinessSettings for a business, or None."""
    try:
        return business.settings
    except BusinessSettings.DoesNotExist:
        return None


def get_storefront_settings(business) -> StorefrontSettings | None:
    """Return the StorefrontSettings for a business, or None."""
    try:
        return business.storefront_settings
    except StorefrontSettings.DoesNotExist:
        return None


def business_slug_exists(slug: str, exclude_id=None) -> bool:
    """Check if a slug is already taken (used in validation)."""
    qs = Business.objects.filter(slug=slug)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()
