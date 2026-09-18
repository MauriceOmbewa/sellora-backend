"""Finances views."""
import logging
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.finances.models import Expense
from apps.finances.selectors import (
    get_cogs_for_period,
    get_expenses_for_business,
    get_revenue_for_period,
    get_total_expenses,
)
from apps.finances.serializers import (
    ExpenseCreateSerializer,
    ExpenseSerializer,
    ExpenseUpdateSerializer,
    FinanceSummarySerializer,
)
from apps.finances.services import create_expense, delete_expense, update_expense
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import created_response, no_content_response, success_response

logger = logging.getLogger("apps")


class FinanceSummaryView(APIView):
    """
    GET /api/v1/businesses/{business_id}/finances/summary/
    Query params: period=7d|30d|90d (default 30d)

    Returns computed P&L summary:
      revenue, cost_of_goods, gross_profit, expenses, net_profit,
      gross_margin%, net_margin%
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        period = request.query_params.get("period", "30d")
        if period not in ("7d", "30d", "90d", "all"):
            period = "30d"

        revenue = get_revenue_for_period(request.business, period)
        cogs = get_cogs_for_period(request.business, period)
        total_expenses = get_total_expenses(request.business, period)

        gross_profit = revenue - cogs
        net_profit = gross_profit - total_expenses

        gross_margin = (
            round(float(gross_profit / revenue) * 100, 1)
            if revenue > 0 else 0.0
        )
        net_margin = (
            round(float(net_profit / revenue) * 100, 1)
            if revenue > 0 else 0.0
        )

        summary = {
            "period": period,
            "revenue": revenue,
            "cost_of_goods": cogs,
            "gross_profit": gross_profit,
            "expenses": total_expenses,
            "net_profit": net_profit,
            "gross_margin": gross_margin,
            "net_margin": net_margin,
        }
        serializer = FinanceSummarySerializer(summary)
        return success_response(data=serializer.data)


class ExpenseListCreateView(APIView):
    """
    GET  /api/v1/businesses/{business_id}/finances/expenses/
    POST /api/v1/businesses/{business_id}/finances/expenses/
    Query params: period=7d|30d|90d, category
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        expenses = get_expenses_for_business(
            request.business,
            period=request.query_params.get("period", "30d"),
            category=request.query_params.get("category"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(expenses, request)
        return paginator.get_paginated_response(
            ExpenseSerializer(page, many=True).data
        )

    def post(self, request, business_id):
        serializer = ExpenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = create_expense(request.business, **serializer.validated_data)
        return created_response(
            data=ExpenseSerializer(expense).data,
            message="Expense recorded."
        )


class ExpenseDetailView(APIView):
    """
    GET    /api/v1/businesses/{business_id}/finances/expenses/{expense_id}/
    PATCH  /api/v1/businesses/{business_id}/finances/expenses/{expense_id}/
    DELETE /api/v1/businesses/{business_id}/finances/expenses/{expense_id}/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_or_404(self, expense_id, business):
        try:
            return Expense.objects.get(id=expense_id, business=business)
        except Expense.DoesNotExist:
            raise ResourceNotFound("Expense not found.")

    def get(self, request, business_id, expense_id):
        expense = self._get_or_404(expense_id, request.business)
        return success_response(data=ExpenseSerializer(expense).data)

    def patch(self, request, business_id, expense_id):
        expense = self._get_or_404(expense_id, request.business)
        serializer = ExpenseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = update_expense(expense, **serializer.validated_data)
        return success_response(
            data=ExpenseSerializer(expense).data,
            message="Expense updated."
        )

    def delete(self, request, business_id, expense_id):
        expense = self._get_or_404(expense_id, request.business)
        delete_expense(expense)
        return no_content_response()


class IncomeListView(APIView):
    """
    GET /api/v1/businesses/{business_id}/finances/income/

    Returns a paginated list of income entries derived from completed, paid
    orders.  Each entry mirrors the data a user needs for a ledger:
      order_id, order_number, customer_name, payment_method, channel,
      amount, date (order created_at), items_summary

    Query params:
      period      = 7d | 30d | 90d | all  (default: 30d)
      search      = free-text (order number or customer name)
      payment_method = mpesa | cash | card | bank_transfer | whatsapp
      page        = int (default: 1)
      page_size   = int (default: 20, max: 100)
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        from apps.orders.models import Order
        from django.db.models import Q
        from common.pagination import StandardResultsPagination
        import logging

        logger = logging.getLogger("apps")

        period         = request.query_params.get("period", "30d")
        search         = request.query_params.get("search", "").strip()
        payment_method = request.query_params.get("payment_method", "")

        # Build date range
        from apps.finances.selectors import get_period_dates
        start, end = get_period_dates(period)

        qs = Order.objects.filter(
            business=request.business,
            status="completed",
            payment_status="paid",
        ).select_related("customer").prefetch_related("items")

        if start:
            qs = qs.filter(created_at__gte=start, created_at__lte=end)
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(customer_name__icontains=search)
            )
        if payment_method:
            qs = qs.filter(payment_method=payment_method)

        qs = qs.order_by("-created_at")

        paginator = StandardResultsPagination()
        page      = paginator.paginate_queryset(qs, request)

        def _item_summary(order):
            items = order.items.all()
            if not items:
                return ""
            parts = [f"{i.product_name} ×{i.quantity}" for i in items[:3]]
            if items.count() > 3:
                parts.append(f"+{items.count() - 3} more")
            return ", ".join(parts)

        data = [
            {
                "id":             str(order.id),
                "order_id":       str(order.id),
                "order_number":   order.order_number,
                "customer_name":  order.customer_name,
                "customer_phone": order.customer_phone,
                "payment_method": order.payment_method,
                "channel":        order.channel,
                "amount":         str(order.total),
                "date":           order.created_at.isoformat(),
                "items_summary":  _item_summary(order),
            }
            for order in page
        ]

        return paginator.get_paginated_response(data)
