"""
API v1 URL configuration.
Each app registers its own urlconf here.
"""

from django.urls import include, path

from apps.messages.urls import whatsapp_urlpatterns
from apps.messages.views.whatsapp_webhook import WhatsAppWebhookView
from apps.payments.urls import (
    billing_urlpatterns,
    mpesa_urlpatterns,
    pochi_urlpatterns,
    plans_urlpatterns,
    payment_configuration_urlpatterns,
)


urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("auth/", include("apps.accounts.urls")),

    # ── File uploads ──────────────────────────────────────────────────────────
    path("", include("apps.core.urls")),

    # ── Pricing plans (public) ────────────────────────────────────────────────
    path(
        "plans/",
        include(
            (plans_urlpatterns, "payments"),
            namespace="plans",
        ),
    ),

    # ── Businesses (includes settings + storefront sub-paths) ────────────────
    path(
        "businesses/",
        include("apps.businesses.urls"),
    ),

    # ── Products & Categories (business-scoped) ───────────────────────────────
    path(
        "businesses/<uuid:business_id>/products/",
        include("apps.products.urls"),
    ),
    path(
        "businesses/<uuid:business_id>/categories/",
        include("apps.categories.urls"),
    ),

    # ── Inventory ─────────────────────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/inventory/",
        include("apps.inventory.urls"),
    ),

    # ── Customers ─────────────────────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/customers/",
        include("apps.customers.urls"),
    ),

    # ── Orders ────────────────────────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/orders/",
        include("apps.orders.urls"),
    ),

    # ── Finances ──────────────────────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/finances/",
        include("apps.finances.urls"),
    ),

    # ── Analytics ─────────────────────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/analytics/",
        include("apps.analytics.urls"),
    ),

    # ── Messages (contact-form inquiries) ─────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/messages/",
        include("apps.messages.urls"),
    ),

    # ── WhatsApp conversations + settings (business-scoped, authenticated) ────
    path(
        "businesses/<uuid:business_id>/whatsapp/",
        include(
            (whatsapp_urlpatterns, "whatsapp"),
            namespace="whatsapp",
        ),
    ),

    # ── Billing (business-scoped) ─────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/billing/",
        include(
            (billing_urlpatterns, "payments"),
            namespace="billing",
        ),
    ),

    # ── WhatsApp webhook (public — AllowAny — Meta POSTs here) ────────────────
    path(
        "webhooks/whatsapp/",
        WhatsAppWebhookView.as_view(),
        name="whatsapp-webhook",
    ),

    # ── Public storefront API (no auth, keyed by slug) ────────────────────────
    path(
        "store/",
        include("apps.businesses.storefront_urls"),
    ),

    # ── M-Pesa API (business-scoped) ──────────────────────────────────────────
    path(
        "payments/",
        include(
            (mpesa_urlpatterns, "payments"),
            namespace="mpesa",
        ),
    ),

    # ── Pochi API (business-scoped) ───────────────────────────────────────────
    path(
        "payments/",
        include(
            (pochi_urlpatterns, "payments"),
            namespace="pochi",
        ),
    ),

    # ── Payment configuration (business-scoped) ───────────────────────────────
    path(
        "payments/",
        include(
            (
                payment_configuration_urlpatterns,
                "payments",
            ),
            namespace="payment-configuration",
        ),
    ),
]