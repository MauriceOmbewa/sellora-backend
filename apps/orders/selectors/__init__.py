"""Order selectors — all read queries."""
from django.db.models import QuerySet
from apps.orders.models import Order


def get_orders_for_business(business, status: str = None,
                             payment_status: str = None,
                             customer_id=None,
                             search: str = None) -> QuerySet:
    """Return orders for a business with optional filters."""
    qs = (
        Order.objects
        .filter(business=business)
        .prefetch_related("items", "timeline")
        .select_related("customer")
    )
    if status:
        qs = qs.filter(status=status)
    if payment_status:
        qs = qs.filter(payment_status=payment_status)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(order_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search)
        )
    return qs.order_by("-created_at")


def get_order_by_id(order_id, business=None) -> Order | None:
    qs = (
        Order.objects
        .filter(id=order_id)
        .prefetch_related("items", "timeline")
        .select_related("customer", "business")
    )
    if business:
        qs = qs.filter(business=business)
    return qs.first()


def get_next_order_number(business) -> str:
    """
    Generate the next sequential order number for a business.
    Format: #1001, #1002, ...
    Uses MAX(order_number) to determine the next value atomically.
    """
    from django.db.models import Max
    last = Order.objects.filter(business=business).aggregate(
        max_num=Max("order_number")
    )["max_num"]

    if last:
        # Strip the # prefix and increment
        try:
            next_num = int(last.lstrip("#")) + 1
        except (ValueError, AttributeError):
            next_num = 1001
    else:
        next_num = 1001

    return f"#{next_num}"
