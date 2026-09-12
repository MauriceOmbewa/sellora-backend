"""
Category signals.

Maintains the denormalized `product_count` on Category.
Called from the products app signals when a product is created,
deleted, or its category changes.

These functions are imported and called by apps/products/signals.py —
not registered as Django signals here (to avoid circular imports).
"""
import logging
from django.db import transaction
from django.db.models import F

logger = logging.getLogger("apps")


def increment_category_product_count(category_id, amount: int = 1):
    """
    Atomically adjust product_count on a Category.

    Args:
        category_id: UUID of the category.
        amount:      +1 when product is added, -1 when removed.
                     Uses F() expression for atomic DB-level update.
    """
    from apps.categories.models import Category
    with transaction.atomic():
        updated = Category.objects.filter(id=category_id).update(
            product_count=F("product_count") + amount
        )
        if updated:
            logger.debug(
                "Category %s product_count adjusted by %d", category_id, amount
            )
