"""
Order model.

Key design decisions:
- customer FK is nullable (guest orders allowed)
- customerName/Phone/Email are denormalized — survive customer record changes
- subtotal/deliveryFee/discount/total stored explicitly — never recomputed from items
- orderNumber is a sequential human-readable string per business (#1001, #1002 ...)
- timeline is stored in OrderTimeline — one row per status transition
"""
from django.db import models
from apps.core.models import BaseModel
from apps.orders.constants import (
    ORDER_STATUS_CHOICES,
    PAYMENT_STATUS_CHOICES,
    PAYMENT_METHOD_CHOICES,
    ORDER_CHANNEL_CHOICES,
)


class Order(BaseModel):

    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )

    # ── Human-readable identifier ─────────────────────────────────────────────
    order_number = models.CharField(max_length=20, db_index=True)

    # ── Denormalized customer snapshot ────────────────────────────────────────
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=30)
    customer_email = models.EmailField(blank=True, default="")
    delivery_address = models.TextField(blank=True, default="")
    order_notes = models.TextField(blank=True, default="")

    # ── Financials ────────────────────────────────────────────────────────────
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ── Status ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default="new",
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cash",
    )
    channel = models.CharField(
        max_length=20,
        choices=ORDER_CHANNEL_CHOICES,
        default="online",
    )

    class Meta:
        db_table = "orders_order"
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        unique_together = [("business", "order_number")]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["business", "payment_status"]),
            models.Index(fields=["customer"]),
        ]

    def __str__(self):
        return f"{self.order_number} — {self.customer_name}"
