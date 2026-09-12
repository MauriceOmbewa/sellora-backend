"""
Business signals.

1. Auto-create BusinessSettings + StorefrontSettings when a Business is created.
   (Belt-and-suspenders alongside the service layer doing the same.)

2. Aggregate counter helpers — called by other apps' signals when their
   records are created/deleted/updated to keep Business counters in sync.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.businesses.models import Business, BusinessSettings, StorefrontSettings

logger = logging.getLogger("apps")


@receiver(post_save, sender=Business)
def create_business_companion_records(sender, instance, created, **kwargs):
    """
    When a new Business is saved for the first time, ensure its companion
    settings records exist.

    Uses get_or_create so it is safe to call multiple times.
    """
    if created:
        BusinessSettings.objects.get_or_create(business=instance)
        StorefrontSettings.objects.get_or_create(business=instance)
        logger.debug(
            "Companion settings created for business %s", instance.id
        )


# ── Aggregate counter utilities ───────────────────────────────────────────────
# Called by other apps (orders, products, customers) to keep denormalized
# counts on the Business model accurate without expensive COUNT() queries.

def increment_business_counter(business_id, field: str, amount: int = 1):
    """
    Atomically increment a counter field on a Business.

    Args:
        business_id: UUID of the business.
        field:       One of 'total_products', 'total_orders', 'total_customers'.
        amount:      Amount to add (use negative to decrement).
    """
    with transaction.atomic():
        Business.objects.filter(id=business_id).update(
            **{field: models_F(field) + amount}
        )


def update_business_revenue(business_id, amount_delta):
    """
    Atomically adjust total_revenue on a Business.

    Args:
        business_id:   UUID of the business.
        amount_delta:  Decimal amount to add (negative for refunds/cancellations).
    """
    with transaction.atomic():
        Business.objects.filter(id=business_id).update(
            total_revenue=models_F("total_revenue") + amount_delta
        )


def models_F(field):
    """Local import of F() to avoid circular import at module level."""
    from django.db.models import F
    return F(field)
