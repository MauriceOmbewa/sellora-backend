"""
Category model.

Each business owns its own set of categories.
Products belong to exactly one category (nullable — products can be uncategorised).

productCount is maintained via signals in signals.py — incremented/decremented
when products are created, deleted, or change category.
"""
from django.db import models

from apps.core.models import BaseModel


class Category(BaseModel):
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="categories",
        db_index=True,
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")

    # Maintained by signals — see apps/categories/signals.py
    product_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "categories_category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "name"]
        # Slug only needs to be unique within a business
        unique_together = [("business", "slug")]

    def __str__(self):
        return f"{self.name} ({self.business.name})"
