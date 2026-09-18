"""
Payments / Billing URL patterns.

Public:
  GET    /api/v1/plans/                         — Pricing plans list

Business-scoped (authenticated):
  GET    /api/v1/businesses/{id}/billing/        — Current billing info
  POST   /api/v1/businesses/{id}/billing/upgrade/  — Upgrade plan (stub)
  POST   /api/v1/businesses/{id}/billing/cancel/   — Cancel subscription (stub)
"""
from django.urls import path
from apps.payments.views import (
    BillingCancelView,
    BillingUpgradeView,
    BusinessBillingView,
    PricingPlansView,
    STKPushView,
    PochiPaymentView,
    PaymentConfigurationView
)

# Plans — public, mounted at /api/v1/plans/ from api/v1/urls.py
plans_urlpatterns = [
    path("", PricingPlansView.as_view(), name="pricing-plans"),
]

# Billing — business-scoped, mounted at /api/v1/businesses/{id}/billing/
billing_urlpatterns = [
    path("", BusinessBillingView.as_view(), name="billing-info"),
    path("upgrade/", BillingUpgradeView.as_view(), name="billing-upgrade"),
    path("cancel/", BillingCancelView.as_view(), name="billing-cancel"),
]

mpesa_urlpatterns = [
    path("stk-push/", STKPushView.as_view(), name="stk-push"),
]

pochi_urlpatterns = [
    path("pochi/", PochiPaymentView.as_view(), name="pochi-payment"),
]

payment_configuration_urlpatterns = [
    path(
        "configuration/<uuid:business_id>/",
        PaymentConfigurationView.as_view(),
        name="payment-configuration",
    ),
]