"""
Analytics URL patterns.
Mounted at /api/v1/businesses/{business_id}/analytics/

GET /summary/           — KPI summary + % change vs prior period
GET /revenue/           — Daily revenue time-series
GET /top-products/      — Top products by revenue
GET /categories/        — Category performance
GET /customer-growth/   — Daily new customer count
"""
from django.urls import path
from apps.analytics.views import (
    AnalyticsSummaryView,
    CategoryPerformanceView,
    CustomerGrowthView,
    MonthlyPerformanceView,
    RevenueTimeSeriesView,
    TopProductsView,
)

urlpatterns = [
    path("summary/",          AnalyticsSummaryView.as_view(),    name="analytics-summary"),
    path("revenue/",          RevenueTimeSeriesView.as_view(),   name="analytics-revenue"),
    path("top-products/",     TopProductsView.as_view(),         name="analytics-top-products"),
    path("categories/",       CategoryPerformanceView.as_view(), name="analytics-categories"),
    path("customer-growth/",  CustomerGrowthView.as_view(),      name="analytics-customer-growth"),
    path("monthly/",          MonthlyPerformanceView.as_view(),  name="analytics-monthly"),
]
