"""Inventory selectors — computed inventory view from products."""
from django.db.models import QuerySet, F
from apps.products.models import Product
from apps.inventory.models import StockAdjustment


def get_inventory_for_business(business, low_stock_only: bool = False) -> QuerySet:
    """
    Return the inventory list — products with their stock info.
    Computed from the products table (not a separate inventory table).
    Optionally filter to only low-stock items.
    """
    qs = (
        Product.objects
        .filter(business=business, status__in=["active", "draft"])
        .select_related("category")
        .order_by("stock_quantity", "name")
    )
    if low_stock_only:
        qs = qs.filter(stock_quantity__lte=F("low_stock_threshold"))
    return qs


def get_stock_adjustments_for_product(product) -> QuerySet:
    """Return all stock adjustments for a product, newest first."""
    return StockAdjustment.objects.filter(product=product).order_by("-created_at")


def get_stock_adjustments_for_business(business) -> QuerySet:
    """Return all stock adjustments across a business's products."""
    return (
        StockAdjustment.objects
        .filter(product__business=business)
        .select_related("product")
        .order_by("-created_at")
    )
