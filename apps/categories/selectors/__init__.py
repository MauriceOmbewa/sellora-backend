"""Category selectors — all read queries for the categories domain."""
from django.db.models import QuerySet

from apps.categories.models import Category


def get_categories_for_business(business, active_only: bool = False) -> QuerySet:
    """Return all categories for a business, ordered by sort_order then name."""
    qs = Category.objects.filter(business=business)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("sort_order", "name")


def get_category_by_id(category_id, business=None) -> Category | None:
    """Return a Category by UUID, optionally scoped to a business."""
    qs = Category.objects.filter(id=category_id)
    if business:
        qs = qs.filter(business=business)
    return qs.first()


def get_category_by_slug(slug: str, business) -> Category | None:
    """Return a Category by slug within a business."""
    return Category.objects.filter(slug=slug, business=business).first()


def category_slug_exists(slug: str, business, exclude_id=None) -> bool:
    """Check if a slug is already taken within a business."""
    qs = Category.objects.filter(slug=slug, business=business)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()
