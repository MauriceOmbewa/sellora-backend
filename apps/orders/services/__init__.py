"""
Order services — the most complex domain in the platform.

create_order:        Validates items, decrements stock, upserts customer,
                     calculates totals, generates order number, appends
                     initial timeline entry, updates business counters.

update_order_status: Enforces state machine transitions, appends timeline
                     entry, triggers post-completion customer stat updates.

cancel_order:        Transitions to cancelled, restores stock.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.orders.constants import (
    ORDER_STATUS_TRANSITIONS,
    DELIVERY_FEE,
    FREE_DELIVERY_THRESHOLD,
)
from apps.orders.models import Order, OrderItem, OrderTimeline
from apps.orders.selectors import get_next_order_number

logger = logging.getLogger("apps")


@transaction.atomic
def create_order(business, *, customer_name: str, customer_phone: str,
                 customer_email: str = "", delivery_address: str = "",
                 order_notes: str = "", payment_method: str = "cash",
                 channel: str = "online", items: list,
                 discount: Decimal = Decimal("0"),
                 custom_delivery_fee: Decimal = None,
                 fulfillment_type: str = "delivery") -> Order:
    """
    Create a new order.

    Steps (all atomic):
      1. Validate each item (product exists, belongs to business, has stock)
      2. Calculate subtotal, delivery fee, total
      3. Upsert customer record from phone number
      4. Generate sequential order number
      5. Create Order + OrderItems
      6. Decrement stock for each item
      7. Append initial timeline entry (status=new)
      8. Update business.total_orders + total_revenue counters

    Args:
        business:          The owning Business.
        customer_name:     Required — denormalized onto order.
        customer_phone:    Required — used to upsert Customer record.
        customer_email:    Optional.
        delivery_address:  Optional.
        order_notes:       Optional.
        payment_method:    One of PAYMENT_METHOD_CHOICES.
        channel:           One of ORDER_CHANNEL_CHOICES.
        items:             List of dicts: [{"product_id": uuid, "quantity": int}]
        discount:          Discount amount in KSh.
        custom_delivery_fee: Override the auto-calculated delivery fee if provided.

    Returns:
        The created Order with items and timeline prefetched.

    Raises:
        ValueError on stock issues or invalid products.
    """
    from apps.products.models import Product

    # ── 1. Validate items and gather product data ─────────────────────────────
    validated_items = []
    subtotal = Decimal("0")

    for item_data in items:
        product_id = item_data.get("product_id")
        quantity = int(item_data.get("quantity", 1))

        if quantity < 1:
            raise ValueError(f"Quantity must be at least 1 (got {quantity}).")

        try:
            from django.db import connection
            if connection.vendor == "postgresql":
                product = Product.objects.select_for_update().get(
                    id=product_id,
                    business=business,
                    status="active",
                )
            else:
                product = Product.objects.get(
                    id=product_id,
                    business=business,
                    status="active",
                )
        except Product.DoesNotExist:
            raise ValueError(
                f"Product {product_id} not found or not available in this business."
            )

        if product.stock_quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.name}': "
                f"requested {quantity}, available {product.stock_quantity}."
            )

        unit_price = product.sale_price or product.selling_price
        item_total = unit_price * quantity
        subtotal += item_total

        validated_items.append({
            "product": product,
            "product_name": product.name,
            "product_image": product.images[0] if product.images else "",
            "sku": product.sku,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": item_total,
        })

    # ── 2. Calculate totals ───────────────────────────────────────────────────
    if custom_delivery_fee is not None:
        delivery_fee = Decimal(str(custom_delivery_fee))
    elif fulfillment_type == "pickup" or channel == "walk-in":
        delivery_fee = Decimal("0")
    else:
        # Read per-business delivery settings, fall back to module constants
        try:
            s = business.settings
            biz_fee       = Decimal(str(s.delivery_fee))
            biz_threshold = Decimal(str(s.free_delivery_threshold))
        except Exception:
            biz_fee       = Decimal(str(DELIVERY_FEE))
            biz_threshold = Decimal(str(FREE_DELIVERY_THRESHOLD))

        delivery_fee = Decimal("0") if subtotal >= biz_threshold else biz_fee

    total = subtotal + delivery_fee - discount

    # ── 3. Upsert customer ────────────────────────────────────────────────────
    from apps.customers.services import upsert_customer
    customer, _ = upsert_customer(
        business,
        name=customer_name,
        phone=customer_phone,
        email=customer_email,
        location=delivery_address,
    )

    # ── 4. Generate order number ──────────────────────────────────────────────
    order_number = get_next_order_number(business)

    # ── 5. Create Order ───────────────────────────────────────────────────────
    order = Order.objects.create(
        business=business,
        customer=customer,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        delivery_address=delivery_address,
        order_notes=order_notes,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        status="new",
        payment_status="pending",
        payment_method=payment_method,
        channel=channel,
    )

    # ── 5b. Create OrderItems + decrement stock ───────────────────────────────
    for item_data in validated_items:
        product = item_data.pop("product")
        OrderItem.objects.create(order=order, product=product, **item_data)

        # Decrement stock atomically
        from django.db.models import F
        Product.objects.filter(id=product.id).update(
            stock_quantity=F("stock_quantity") - item_data["quantity"]
        )

    # ── 6. Append initial timeline entry ─────────────────────────────────────
    OrderTimeline.objects.create(
        order=order,
        status="new",
        note="Order placed.",
    )

    # ── 7. Update business counters ───────────────────────────────────────────
    from apps.businesses.signals import (
        increment_business_counter,
        update_business_revenue,
    )
    increment_business_counter(business.id, "total_orders", 1)
    update_business_revenue(business.id, total)

    # ── 8. Update business total_customers if new customer ───────────────────
    from apps.businesses.signals import increment_business_counter as inc
    # Only count unique customers — check if this is their first order
    if customer.total_orders == 0:
        inc(business.id, "total_customers", 1)

    logger.info(
        "Order %s created for business %s — total KSh %s",
        order_number, business.id, total,
    )

    # ── 9. Dispatch notification tasks (after transaction commits) ────────────
    # Use on_commit to avoid firing tasks on rolled-back transactions
    from django.db import connection
    from django.db.transaction import on_commit
    on_commit(lambda: _dispatch_new_order_notifications(str(order.id)))

    return order


def _dispatch_new_order_notifications(order_id: str):
    """Fire notification tasks after the order transaction commits."""
    try:
        from apps.notifications.tasks import send_new_order_email
        send_new_order_email.delay(order_id)
    except Exception as exc:
        logger.warning("Failed to dispatch new order notifications: %s", exc)


@transaction.atomic
def update_order_status(order: Order, new_status: str,
                        note: str = "") -> Order:
    """
    Transition an order to a new status.

    Enforces the state machine — only valid transitions are allowed.
    Appends an OrderTimeline entry on every transition.
    On completion → updates customer stats.
    On cancellation → restores stock.

    Args:
        order:      The Order to update.
        new_status: Target status.
        note:       Optional note appended to the timeline entry.

    Returns:
        The updated Order.

    Raises:
        ValueError if the transition is invalid.
    """
    allowed = ORDER_STATUS_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{order.status}' to '{new_status}'. "
            f"Allowed: {allowed or 'none (terminal state)'}."
        )

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    # Append timeline entry
    OrderTimeline.objects.create(
        order=order,
        status=new_status,
        note=note or _default_note(new_status),
    )

    # Post-completion: update customer stats
    if new_status == "completed" and order.customer:
        from apps.customers.services import update_customer_order_stats
        update_customer_order_stats(order.customer, order.total, is_new_order=True)

    # Cancellation: restore stock
    if new_status == "cancelled":
        _restore_stock(order)
        # Reverse business revenue counter
        from apps.businesses.signals import update_business_revenue
        update_business_revenue(order.business_id, -order.total)

    # Notify customer of status change
    from django.db.transaction import on_commit
    on_commit(lambda: _dispatch_status_notification(str(order.id), new_status))

    logger.info("Order %s → %s", order.order_number, new_status)
    return order


def _dispatch_status_notification(order_id: str, new_status: str):
    try:
        from apps.notifications.tasks import send_order_status_email
        send_order_status_email.delay(order_id, new_status)
    except Exception as exc:
        logger.warning("Failed to dispatch order status notification: %s", exc)


def _restore_stock(order: Order):
    """Restore stock quantities for all items in a cancelled order."""
    from django.db.models import F
    from apps.products.models import Product

    # Re-fetch items from DB to ensure we have the latest data
    for item in order.items.select_related("product").all():
        if item.product_id:
            Product.objects.filter(id=item.product_id).update(
                stock_quantity=F("stock_quantity") + item.quantity
            )


def _default_note(status: str) -> str:
    notes = {
        "confirmed": "Order confirmed.",
        "processing": "Order is being processed.",
        "ready": "Order is ready for pickup/delivery.",
        "completed": "Order completed.",
        "cancelled": "Order cancelled.",
    }
    return notes.get(status, "")


@transaction.atomic
def cancel_order(order: Order, note: str = "") -> Order:
    """Convenience wrapper for cancelling an order."""
    return update_order_status(
        order, "cancelled", note=note or "Order cancelled."
    )
