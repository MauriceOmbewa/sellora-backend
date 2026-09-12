"""
StorefrontSettings — controls what is displayed on the public storefront.

1:1 with Business. Created automatically via signal when a Business is created.
"""
from django.db import models

from apps.core.models import BaseModel


class StorefrontSettings(BaseModel):
    """
    Storefront display configuration.

    Separating this from Business keeps the main model lean and makes
    the publish/unpublish action explicit.

    Accessed at:  GET/PUT  /api/v1/businesses/{id}/storefront/
                  POST     /api/v1/businesses/{id}/storefront/publish/
    """

    business = models.OneToOneField(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="storefront_settings",
    )

    # ── Featured content ──────────────────────────────────────────────────────
    # Stored as arrays of UUIDs — resolved to objects by the storefront API
    featured_product_ids = models.JSONField(default=list, blank=True)
    featured_category_ids = models.JSONField(default=list, blank=True)

    # ── Section toggles ───────────────────────────────────────────────────────
    show_new_arrivals = models.BooleanField(default=True)
    show_best_sellers = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=False)

    # ── Publish state ─────────────────────────────────────────────────────────
    is_published = models.BooleanField(default=False, db_index=True)
    last_published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "businesses_storefront_settings"
        verbose_name = "Storefront Settings"
        verbose_name_plural = "Storefront Settings"

    def __str__(self):
        status = "published" if self.is_published else "unpublished"
        return f"Storefront for {self.business.name} ({status})"
