"""
API v1 URL configuration.
Each app registers its own urlconf here.
"""
from django.urls import path, include
from apps.payments.urls import plans_urlpatterns, billing_urlpatterns

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("auth/", include("apps.accounts.urls")),

    # ── File uploads ──────────────────────────────────────────────────────────
    path("", include("apps.core.urls")),

    # ── Pricing plans (public) ────────────────────────────────────────────────
    path("plans/", include((plans_urlpatterns, "payments"), namespace="plans")),

    # ── Businesses (includes settings + storefront sub-paths) ─────────────────
    path("businesses/", include("apps.businesses.urls")),

    # ── Products & Categories (business-scoped) ───────────────────────────────
    path("businesses/<uuid:business_id>/products/", include("apps.products.urls")),
    path("businesses/<uuid:business_id>/categories/", include("apps.categories.urls")),

    # ── Inventory ─────────────────────────────────────────────────────────────
    path("businesses/<uuid:business_id>/inventory/", include("apps.inventory.urls")),

    # ── Customers ─────────────────────────────────────────────────────────────
    path("businesses/<uuid:business_id>/customers/", include("apps.customers.urls")),

    # ── Orders ────────────────────────────────────────────────────────────────
    path("businesses/<uuid:business_id>/orders/", include("apps.orders.urls")),

    # ── Finances ──────────────────────────────────────────────────────────────
    path("businesses/<uuid:business_id>/finances/", include("apps.finances.urls")),

    # ── Analytics ─────────────────────────────────────────────────────────────
    path("businesses/<uuid:business_id>/analytics/", include("apps.analytics.urls")),

    # ── Messages (customer inquiries) ─────────────────────────────────────────
    path("businesses/<uuid:business_id>/messages/", include("apps.messages.urls")),

    # ── Billing (business-scoped) ─────────────────────────────────────────────
    path(
        "businesses/<uuid:business_id>/billing/",
        include((billing_urlpatterns, "payments"), namespace="billing"),
    ),

    # ── Public storefront API (no auth, keyed by slug) ────────────────────────
    path("store/", include("apps.businesses.storefront_urls")),
]
