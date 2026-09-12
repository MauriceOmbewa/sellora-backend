"""
OrderItem — one line in an order.

Product fields are denormalized (name, sku, image) so the order record
remains accurate even if the product is later renamed or deleted.
"""
from django.db import models
from apps.core.models import BaseModel


class OrderItem(BaseModel):

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="order_items",
    )

    # ── Denormalized product snapshot ────────────────────────────────────────
    product_name = models.CharField(max_length=255)
    product_image = models.URLField(max_length=500, blank=True, default="")
    sku = models.CharField(max_length=100, blank=True, default="")

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "orders_order_item"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"
