"""
StockAdjustment — audit log for every stock change.
"""
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


class StockAdjustment(BaseModel):

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="stock_adjustments",
    )
    quantity_delta = models.IntegerField(
        help_text="Signed integer: positive = added, negative = removed."
    )
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()
    reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "inventory_stock_adjustment"
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
        ordering = ["-created_at"]

    def __str__(self):
        direction = "+" if self.quantity_delta >= 0 else ""
        return (
            f"{self.product.name}: {direction}{self.quantity_delta} "
            f"({self.previous_stock}→{self.new_stock})"
        )
