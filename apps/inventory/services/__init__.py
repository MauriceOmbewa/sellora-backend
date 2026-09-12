"""
Inventory services stub.
Full implementation in Phase 4 (Step 12).
create_stock_adjustment is needed now by products.services.adjust_stock.
"""
import logging
from django.db import transaction

logger = logging.getLogger("apps")


@transaction.atomic
def create_stock_adjustment(product, *, quantity_delta: int,
                            previous_stock: int, new_stock: int,
                            reason: str = "") -> "StockAdjustment":
    """
    Create a StockAdjustment audit record.
    Called by products.services.adjust_stock after updating stock_quantity.
    """
    from apps.inventory.models import StockAdjustment

    adjustment = StockAdjustment.objects.create(
        product=product,
        quantity_delta=quantity_delta,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=reason,
    )
    logger.debug(
        "StockAdjustment created for product %s: delta=%d (%d→%d)",
        product.id, quantity_delta, previous_stock, new_stock,
    )
    return adjustment
