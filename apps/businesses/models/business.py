"""
Business model — the central tenant entity.

Every resource in the platform (products, orders, customers, etc.) is
scoped to a Business. One user can own multiple businesses.
"""
from django.db import models
from django.conf import settings

from apps.core.models import BaseModel
from apps.businesses.constants import (
    BUSINESS_CATEGORY_CHOICES,
    BUSINESS_STATUS_CHOICES,
    BUSINESS_PLAN_CHOICES,
    DEFAULT_THEME,
    DEFAULT_CONTACT,
    DEFAULT_SOCIAL_LINKS,
    DEFAULT_HERO,
)


class Business(BaseModel):
    """
    A merchant's business on the Sellora platform.

    Identified publicly by `slug` (used in storefront URLs).
    Identified internally by `id` (UUID, used in dashboard API URLs).
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
        db_index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-safe identifier used in storefront URLs e.g. /store/maison-aura/",
    )
    category = models.CharField(
        max_length=50,
        choices=BUSINESS_CATEGORY_CHOICES,
        default="other",
    )
    description = models.TextField(blank=True, default="")
    motto = models.CharField(max_length=255, blank=True, default="")

    # ── Branding ──────────────────────────────────────────────────────────────
    logo = models.URLField(max_length=500, blank=True, default="")
    favicon = models.URLField(max_length=500, blank=True, default="")

    # ── Status & Plan ─────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=BUSINESS_STATUS_CHOICES,
        default="active",
        db_index=True,
    )
    plan = models.CharField(
        max_length=20,
        choices=BUSINESS_PLAN_CHOICES,
        default="starter",
    )

    # ── JSON fields (stored as JSONB in PostgreSQL) ───────────────────────────
    # Using JSONField gives us a proper Python dict; no string parsing needed.
    theme = models.JSONField(default=dict, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    hero = models.JSONField(default=dict, blank=True)

    about_text = models.TextField(blank=True, default="")

    # ── Denormalized aggregate counters (maintained by signals/services) ──────
    # Stored here so the dashboard overview can fetch them in a single query
    # without expensive COUNT() aggregations on every page load.
    total_products = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_customers = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "businesses_business"
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        """Set default JSON field values on first save."""
        if not self.theme:
            self.theme = DEFAULT_THEME.copy()
        if not self.contact:
            self.contact = DEFAULT_CONTACT.copy()
        if not self.social_links:
            self.social_links = DEFAULT_SOCIAL_LINKS.copy()
        if not self.hero:
            self.hero = DEFAULT_HERO.copy()
        super().save(*args, **kwargs)
