"""Customer services — all write operations."""
import logging
from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.customers.selectors import get_customer_by_phone

logger = logging.getLogger("apps")


@transaction.atomic
def upsert_customer(business, *, name: str, phone: str,
                    email: str = "", location: str = "") -> tuple[Customer, bool]:
    """
    Get or create a customer by phone number within a business.

    Called automatically when an order is placed — the customer record
    is never created manually via the dashboard UI.

    If the customer exists, we update name/email if they've changed
    (e.g. customer used a different name on a repeat order).

    Returns:
        (customer, created) — created=True for brand new customers.
    """
    customer = get_customer_by_phone(phone, business)

    if customer:
        updated = False
        if name and customer.name != name:
            customer.name = name
            updated = True
        if email and customer.email != email:
            customer.email = email
            updated = True
        if location and customer.location != location:
            customer.location = location
            updated = True
        if updated:
            customer.save(update_fields=["name", "email", "location", "updated_at"])
        return customer, False

    customer = Customer.objects.create(
        business=business,
        name=name,
        phone=phone,
        email=email or "",
        location=location or "",
        first_purchase_at=timezone.now(),
    )
    logger.info("New customer created: %s (%s) for business %s",
                name, phone, business.id)
    return customer, True


@transaction.atomic
def update_customer_order_stats(customer: Customer, order_total,
                                 is_new_order: bool = True) -> Customer:
    """
    Update customer aggregate stats after an order is completed.

    Args:
        customer:     The Customer to update.
        order_total:  The order's total amount.
        is_new_order: True to increment, False to decrement (on cancellation).
    """
    from django.db.models import F

    if is_new_order:
        Customer.objects.filter(id=customer.id).update(
            total_orders=F("total_orders") + 1,
            total_spent=F("total_spent") + order_total,
            last_purchase_at=timezone.now(),
        )
    else:
        Customer.objects.filter(id=customer.id).update(
            total_orders=F("total_orders") - 1,
            total_spent=F("total_spent") - order_total,
        )
    customer.refresh_from_db()
    return customer


@transaction.atomic
def update_customer(customer: Customer, **fields) -> Customer:
    """Manual update from dashboard (notes, tags, status)."""
    allowed = {"notes", "tags", "status", "name", "email", "location"}
    update_fields = []
    for field, value in fields.items():
        if field in allowed:
            setattr(customer, field, value)
            update_fields.append(field)
    update_fields.append("updated_at")
    customer.save(update_fields=update_fields)
    return customer
