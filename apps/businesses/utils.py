"""
Business utility functions.
"""
from django.utils.text import slugify as django_slugify

from apps.businesses.models import Business


def generate_unique_slug(name: str, exclude_id=None) -> str:
    """
    Generate a unique URL-safe slug from a business name.

    Strategy:
      1. Slugify the name (e.g. "Maison Aura" → "maison-aura")
      2. If that slug is taken, append an incrementing number:
         "maison-aura-2", "maison-aura-3", ...

    Args:
        name:       The business name to base the slug on.
        exclude_id: If updating an existing business, pass its ID to avoid
                    a false collision with itself.

    Returns:
        A slug string guaranteed to be unique in the Business table.
    """
    base_slug = django_slugify(name)

    # Truncate to leave room for a numeric suffix
    if len(base_slug) > 90:
        base_slug = base_slug[:90]

    slug = base_slug
    counter = 2

    qs = Business.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
