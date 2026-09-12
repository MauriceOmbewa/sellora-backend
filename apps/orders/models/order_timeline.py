"""
OrderTimeline — immutable audit log of every status transition.

One record is appended each time an order status changes.
Never updated or deleted — append-only.
"""
from django.db import models
from apps.orders.constants import ORDER_STATUS_CHOICES


class OrderTimeline(models.Model):
    """Intentionally does NOT inherit BaseModel — we want auto-generated PK."""

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="timeline",
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES)
    note = models.CharField(max_length=500, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders_order_timeline"
        verbose_name = "Order Timeline Entry"
        verbose_name_plural = "Order Timeline"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.order.order_number} → {self.status} at {self.timestamp}"
