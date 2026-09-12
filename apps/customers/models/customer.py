"""
Customer model.

Customers are NOT manually created — they are auto-created (or upserted)
when an order is placed, using customerPhone as the unique identifier
within a business.

totalOrders, totalSpent, lastPurchaseAt are maintained by order signals.
"""
from django.db import models
from apps.core.models import BaseModel


class Customer(BaseModel):

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="customers",
        db_index=True,
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")

    # ── Maintained by order signals ───────────────────────────────────────────
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_purchase_at = models.DateTimeField(null=True, blank=True)
    first_purchase_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "customers_customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-created_at"]
        # Phone must be unique per business — same number can exist in different businesses
        unique_together = [("business", "phone")]

    def __str__(self):
        return f"{self.name} ({self.phone})"
