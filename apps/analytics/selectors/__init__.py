"""
Analytics selectors — all aggregation queries.

All data is computed on-the-fly from existing tables (orders, products,
customers). No separate analytics table needed at this scale.

Every selector accepts a (business, period) pair.
period: '7d' | '30d' | '90d'
"""
from datetime import timedelta
from decimal import Decimal
from django.db.models import (
    Count, Sum, Avg, F, Q,
    ExpressionWrapper, DecimalField,
    FloatField, Value,
)
from django.db.models.functions import TruncDate, TruncDay, Coalesce
from django.utils import timezone


def _get_period_range(period: str):
    """Return (current_start, current_end, previous_start, previous_end)."""
    now = timezone.now()
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 30)

    current_start = now - timedelta(days=days)
    current_end = now
    previous_start = current_start - timedelta(days=days)
    previous_end = current_start

    return current_start, current_end, previous_start, previous_end


def _pct_change(current, previous) -> float:
    """Calculate percentage change, return 0.0 if previous is zero."""
    if not previous or previous == 0:
        return 0.0
    return round(float((current - previous) / previous) * 100, 1)


def get_analytics_summary(business, period: str = "30d") -> dict:
    """
    Compute the full AnalyticsSummary.

    Returns:
        {
            total_revenue, total_orders, total_customers, average_order_value,
            revenue_change, orders_change, customers_change, aov_change  (% vs prior period)
        }
    """
    from apps.orders.models import Order
    from apps.customers.models import Customer

    cur_start, cur_end, prev_start, prev_end = _get_period_range(period)

    def _order_qs(start, end):
        return Order.objects.filter(
            business=business,
            status="completed",
            created_at__gte=start,
            created_at__lte=end,
        )

    # ── Current period ────────────────────────────────────────────────────────
    cur_orders = _order_qs(cur_start, cur_end)
    cur_agg = cur_orders.aggregate(
        revenue=Coalesce(Sum("total"), Decimal("0")),
        count=Count("id"),
        avg=Coalesce(Avg("total"), Decimal("0")),
    )

    cur_customers = Customer.objects.filter(
        business=business,
        created_at__gte=cur_start,
        created_at__lte=cur_end,
    ).count()

    # ── Previous period ───────────────────────────────────────────────────────
    prev_orders = _order_qs(prev_start, prev_end)
    prev_agg = prev_orders.aggregate(
        revenue=Coalesce(Sum("total"), Decimal("0")),
        count=Count("id"),
        avg=Coalesce(Avg("total"), Decimal("0")),
    )
    prev_customers = Customer.objects.filter(
        business=business,
        created_at__gte=prev_start,
        created_at__lte=prev_end,
    ).count()

    return {
        "period": period,
        "total_revenue": cur_agg["revenue"],
        "total_orders": cur_agg["count"],
        "total_customers": cur_customers,
        "average_order_value": cur_agg["avg"],
        "revenue_change": _pct_change(cur_agg["revenue"], prev_agg["revenue"]),
        "orders_change": _pct_change(cur_agg["count"], prev_agg["count"]),
        "customers_change": _pct_change(cur_customers, prev_customers),
        "aov_change": _pct_change(cur_agg["avg"], prev_agg["avg"]),
    }


def get_revenue_time_series(business, period: str = "30d") -> list:
    """
    Return daily revenue + order count time-series for the period.
    Each entry: { date, revenue, orders }
    """
    from apps.orders.models import Order

    cur_start, cur_end, _, _ = _get_period_range(period)

    rows = (
        Order.objects
        .filter(
            business=business,
            status="completed",
            created_at__gte=cur_start,
            created_at__lte=cur_end,
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            revenue=Coalesce(Sum("total"), Decimal("0")),
            orders=Count("id"),
        )
        .order_by("day")
    )

    return [
        {
            "date": row["day"].isoformat(),
            "revenue": float(row["revenue"]),
            "orders": row["orders"],
        }
        for row in rows
    ]


def get_top_products(business, period: str = "30d", limit: int = 5) -> list:
    """
    Return top-selling products by revenue in the period.
    Each entry: { product_id, product_name, total_sold, revenue, percentage_of_total }
    """
    from apps.orders.models import Order, OrderItem

    cur_start, cur_end, _, _ = _get_period_range(period)

    completed_orders = Order.objects.filter(
        business=business,
        status="completed",
        created_at__gte=cur_start,
        created_at__lte=cur_end,
    )

    items = (
        OrderItem.objects
        .filter(order__in=completed_orders)
        .values("product", "product_name")
        .annotate(
            total_sold=Sum("quantity"),
            revenue=Coalesce(Sum("total_price"), Decimal("0")),
        )
        .order_by("-revenue")[:limit]
    )

    # Calculate total revenue for percentage
    total_rev = sum(float(i["revenue"]) for i in items) or 1

    return [
        {
            "product_id": str(item["product"]) if item["product"] else None,
            "product_name": item["product_name"],
            "total_sold": item["total_sold"],
            "revenue": float(item["revenue"]),
            "percentage_of_total": round(float(item["revenue"]) / total_rev * 100, 1),
        }
        for item in items
    ]


def get_category_performance(business, period: str = "30d") -> list:
    """
    Return revenue and units sold per category in the period.
    Each entry: { category_id, category_name, total_sold, revenue, percentage_of_total }
    """
    from apps.orders.models import Order, OrderItem

    cur_start, cur_end, _, _ = _get_period_range(period)

    completed_orders = Order.objects.filter(
        business=business,
        status="completed",
        created_at__gte=cur_start,
        created_at__lte=cur_end,
    )

    items = (
        OrderItem.objects
        .filter(order__in=completed_orders, product__isnull=False)
        .values(
            category_id=F("product__category__id"),
            category_name=F("product__category__name"),
        )
        .annotate(
            total_sold=Sum("quantity"),
            revenue=Coalesce(Sum("total_price"), Decimal("0")),
        )
        .order_by("-revenue")
    )

    total_rev = sum(float(i["revenue"]) for i in items) or 1

    return [
        {
            "category_id": str(item["category_id"]) if item["category_id"] else None,
            "category_name": item["category_name"] or "Uncategorised",
            "total_sold": item["total_sold"],
            "revenue": float(item["revenue"]),
            "percentage_of_total": round(float(item["revenue"]) / total_rev * 100, 1),
        }
        for item in items
    ]


def get_customer_growth(business, period: str = "30d") -> list:
    """
    Return daily new vs returning customer counts.
    Each entry: { date, new_customers, returning_customers, total_customers }
    """
    from apps.orders.models import Order
    from django.db.models import IntegerField

    cur_start, cur_end, _, _ = _get_period_range(period)

    # New customers: first_purchase_at falls within the period
    from apps.customers.models import Customer

    rows = (
        Customer.objects
        .filter(
            business=business,
            first_purchase_at__gte=cur_start,
            first_purchase_at__lte=cur_end,
        )
        .annotate(day=TruncDate("first_purchase_at"))
        .values("day")
        .annotate(new_customers=Count("id"))
        .order_by("day")
    )

    return [
        {
            "date": row["day"].isoformat(),
            "new_customers": row["new_customers"],
        }
        for row in rows
    ]


def get_monthly_performance(business, year: int) -> list:
    """
    Return month-by-month revenue, expenses, and net profit for a given year.

    Each entry:
        { month: 1..12, month_name: 'Jan', revenue, expenses, net_profit, orders }

    Revenue = sum of completed order totals in that calendar month.
    Expenses = sum of expense records dated in that calendar month.
    Net profit = revenue - expenses  (may be negative).
    """
    from apps.orders.models import Order
    from apps.finances.models import Expense
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    import calendar

    month_names = ['Jan','Feb','Mar','Apr','May','Jun',
                   'Jul','Aug','Sep','Oct','Nov','Dec']

    # Revenue by month (completed orders only, keyed by month number)
    order_rows = (
        Order.objects
        .filter(
            business=business,
            status='completed',
            created_at__year=year,
        )
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            revenue=Sum('total'),
            orders=Count('id'),
        )
    )
    rev_map = {}
    ord_map = {}
    for row in order_rows:
        m = row['month'].month
        rev_map[m] = float(row['revenue'] or 0)
        ord_map[m] = row['orders'] or 0

    # Expenses by month (keyed by month number)
    expense_rows = (
        Expense.objects
        .filter(
            business=business,
            date__year=year,
        )
        .values('date__month')
        .annotate(expenses=Sum('amount'))
    )
    exp_map = {row['date__month']: float(row['expenses'] or 0) for row in expense_rows}

    result = []
    for m in range(1, 13):
        revenue  = rev_map.get(m, 0.0)
        expenses = exp_map.get(m, 0.0)
        result.append({
            'month':      m,
            'month_name': month_names[m - 1],
            'revenue':    revenue,
            'expenses':   expenses,
            'net_profit': revenue - expenses,
            'orders':     ord_map.get(m, 0),
        })

    return result
