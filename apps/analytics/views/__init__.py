"""
Analytics views — all read-only, computed from existing data.
"""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.analytics.selectors import (
    get_analytics_summary,
    get_category_performance,
    get_customer_growth,
    get_monthly_performance,
    get_revenue_time_series,
    get_top_products,
)
from apps.analytics.serializers import (
    AnalyticsSummarySerializer,
    CategoryPerformanceSerializer,
    CustomerGrowthSerializer,
    RevenueDataPointSerializer,
    TopProductSerializer,
)
from common.responses import success_response

logger = logging.getLogger("apps")

VALID_PERIODS = ("7d", "30d", "90d")


def _get_period(request) -> str:
    period = request.query_params.get("period", "30d")
    return period if period in VALID_PERIODS else "30d"


class AnalyticsSummaryView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/summary/
    ?period=7d|30d|90d

    Returns KPI summary with % change vs prior period:
    total_revenue, total_orders, total_customers, average_order_value,
    revenue_change, orders_change, customers_change, aov_change
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = _get_period(request)
        summary = get_analytics_summary(request.business, period)
        return success_response(
            data=AnalyticsSummarySerializer(summary).data
        )


class RevenueTimeSeriesView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/revenue/
    ?period=7d|30d|90d

    Daily revenue + order count for charting.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = _get_period(request)
        data = get_revenue_time_series(request.business, period)
        return success_response(
            data=RevenueDataPointSerializer(data, many=True).data
        )


class TopProductsView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/top-products/
    ?period=7d|30d|90d&limit=5
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = _get_period(request)
        try:
            limit = min(int(request.query_params.get("limit", 5)), 20)
        except (ValueError, TypeError):
            limit = 5

        data = get_top_products(request.business, period, limit=limit)
        return success_response(
            data=TopProductSerializer(data, many=True).data
        )


class CategoryPerformanceView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/categories/
    ?period=7d|30d|90d
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = _get_period(request)
        data = get_category_performance(request.business, period)
        return success_response(
            data=CategoryPerformanceSerializer(data, many=True).data
        )


class CustomerGrowthView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/customer-growth/
    ?period=7d|30d|90d
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = _get_period(request)
        data = get_customer_growth(request.business, period)
        return success_response(
            data=CustomerGrowthSerializer(data, many=True).data
        )


class MonthlyPerformanceView(APIView):
    """
    GET /api/v1/businesses/{business_id}/analytics/monthly/
    ?year=2026   (defaults to current year)

    Returns 12 rows — one per calendar month — with:
      month, month_name, revenue, expenses, net_profit, orders
    Always returns all 12 months; months with no data have zeros.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        from django.utils import timezone

        try:
            year = int(request.query_params.get("year", timezone.now().year))
        except (ValueError, TypeError):
            year = timezone.now().year

        # Clamp to a sensible range
        current_year = timezone.now().year
        year = max(2020, min(year, current_year))

        data = get_monthly_performance(request.business, year)
        return success_response(data=data)
