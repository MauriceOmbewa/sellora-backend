"""
Finances URL patterns.
Mounted at /api/v1/businesses/{business_id}/finances/

GET    /summary/                        P&L summary (computed)
GET    /expenses/                       List expenses
POST   /expenses/                       Create expense
GET    /expenses/{expense_id}/          Expense detail
PATCH  /expenses/{expense_id}/          Update expense
DELETE /expenses/{expense_id}/          Delete expense
"""
from django.urls import path
from apps.finances.views import (
    ExpenseDetailView,
    ExpenseListCreateView,
    FinanceSummaryView,
    IncomeListView,
)

urlpatterns = [
    path("summary/",                     FinanceSummaryView.as_view(),     name="finance-summary"),
    path("income/",                      IncomeListView.as_view(),          name="finance-income"),
    path("expenses/",                    ExpenseListCreateView.as_view(),   name="expense-list-create"),
    path("expenses/<uuid:expense_id>/",  ExpenseDetailView.as_view(),       name="expense-detail"),
]
