"""
Product model — the core catalogue entity.

Key design decisions:
  - category is nullable with SET_NULL so deleting a category doesn't
    delete its products (matches frontend confirmation message).
  - costPrice is private — never serialized in public storefront responses.
  - images is a JSONField storing an ordered list of image URLs.
  - totalSold is maintained by the orders signals — not computed on read.
  - slug is unique within a business (unique_together).
"""
import uuid
from django.db import models
from apps.core.models import BaseModel
from apps.products.constants import PRODUCT_STATUS_CHOICES, PRODUCT_BADGE_CHOICES


class Product(BaseModel):

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True,
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, default="")

    # ── Media ─────────────────────────────────────────────────────────────────
    # Ordered list of image URLs — first image is the primary display image
    images = models.JSONField(default=list, blank=True)

    # ── Pricing ───────────────────────────────────────────────────────────────
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Private — never expose in public storefront responses.",
    )
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    # ── Inventory ─────────────────────────────────────────────────────────────
    sku = models.CharField(max_length=100, blank=True, default="")
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    # ── Status & Visibility ───────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=PRODUCT_STATUS_CHOICES,
        default="draft",
        db_index=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Toggles storefront visibility without changing status.",
    )

    # ── Merchandising ─────────────────────────────────────────────────────────
    badge = models.CharField(
        max_length=20,
        choices=PRODUCT_BADGE_CHOICES,
        blank=True,
        default="",
    )
    tags = models.JSONField(default=list, blank=True)

    # ── Denormalized counter (maintained by orders signals) ───────────────────
    total_sold = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "products_product"
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        unique_together = [("business", "slug")]
        indexes = [
            models.Index(fields=["business", "status", "is_available"]),
            models.Index(fields=["business", "is_featured"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.business.name})"

    @property
    def stock_status(self) -> str:
        """Computed stock status — used in inventory views."""
        if self.stock_quantity == 0:
            return "out-of-stock"
        if self.stock_quantity <= self.low_stock_threshold:
            return "low-stock"
        return "in-stock"

    @property
    def display_price(self):
        """The price shown to customers — sale_price if set, else selling_price."""
        return self.sale_price if self.sale_price else self.selling_price
