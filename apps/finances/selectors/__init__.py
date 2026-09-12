"""Finances selectors."""
from datetime import timedelta
from decimal import Decimal
from django.db.models import QuerySet, Sum
from django.utils import timezone

from apps.finances.models import Expense


def get_period_dates(period: str):
    """
    Return (start_date, end_date) for a named period.
    period: '7d' | '30d' | '90d' | 'all'
    """
    now = timezone.now()
    periods = {"7d": 7, "30d": 30, "90d": 90}
    days = periods.get(period)
    if days:
        return now - timedelta(days=days), now
    return None, now  # 'all' — no start bound


def get_expenses_for_business(business, period: str = "30d",
                               category: str = None) -> QuerySet:
    qs = Expense.objects.filter(business=business)
    start, end = get_period_dates(period)
    if start:
        qs = qs.filter(date__gte=start.date(), date__lte=end.date())
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-date")


def get_total_expenses(business, period: str = "30d") -> Decimal:
    qs = get_expenses_for_business(business, period=period)
    result = qs.aggregate(total=Sum("amount"))["total"]
    return result or Decimal("0")


def get_revenue_for_period(business, period: str = "30d") -> Decimal:
    """
    Sum total from completed orders in the period.
    Revenue = sum of order totals where status='completed'.
    """
    from apps.orders.models import Order
    start, end = get_period_dates(period)
    qs = Order.objects.filter(
        business=business,
        status="completed",
    )
    if start:
        qs = qs.filter(created_at__gte=start, created_at__lte=end)
    result = qs.aggregate(total=Sum("total"))["total"]
    return result or Decimal("0")


def get_cogs_for_period(business, period: str = "30d") -> Decimal:
    """
    Cost of Goods Sold = sum of (cost_price × quantity) for completed order items.
    """
    from apps.orders.models import Order, OrderItem
    from django.db.models import F, ExpressionWrapper, DecimalField

    start, end = get_period_dates(period)
    order_qs = Order.objects.filter(business=business, status="completed")
    if start:
        order_qs = order_qs.filter(created_at__gte=start, created_at__lte=end)

    result = (
        OrderItem.objects
        .filter(order__in=order_qs, product__isnull=False)
        .annotate(
            line_cost=ExpressionWrapper(
                F("quantity") * F("product__cost_price"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .aggregate(total=Sum("line_cost"))["total"]
    )
    return result or Decimal("0")
