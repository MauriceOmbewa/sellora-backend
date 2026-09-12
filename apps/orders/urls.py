"""
Order URL patterns.
Mounted at /api/v1/businesses/{business_id}/orders/

GET    /                       List orders
POST   /                       Create order (dashboard)
GET    /{order_id}/            Order detail
PATCH  /{order_id}/status/     Update order status (state machine)
PATCH  /{order_id}/payment-status/  Update payment status
"""
from django.urls import path
from apps.orders.views import (
    OrderDetailView,
    OrderListCreateView,
    OrderPaymentStatusView,
    OrderStatusUpdateView,
)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("<uuid:order_id>/status/", OrderStatusUpdateView.as_view(), name="order-status-update"),
    path("<uuid:order_id>/payment-status/", OrderPaymentStatusView.as_view(), name="order-payment-status"),
]
