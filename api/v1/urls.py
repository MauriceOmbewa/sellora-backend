"""
API v1 URL configuration.

Each app registers its own router/urlconf here.
Populated progressively as apps are built.
"""
from django.urls import path, include

urlpatterns = [
    # Auth
    path("auth/", include("apps.accounts.urls")),

    # Business management
    path("businesses/", include("apps.businesses.urls")),

    # Products & Categories
    path("businesses/<uuid:business_id>/products/", include("apps.products.urls")),
    path("businesses/<uuid:business_id>/categories/", include("apps.categories.urls")),

    # Inventory
    path("businesses/<uuid:business_id>/inventory/", include("apps.inventory.urls")),

    # Customers
    path("businesses/<uuid:business_id>/customers/", include("apps.customers.urls")),

    # Orders
    path("businesses/<uuid:business_id>/orders/", include("apps.orders.urls")),

    # Finances
    path("businesses/<uuid:business_id>/finances/", include("apps.finances.urls")),

    # Analytics
    path("businesses/<uuid:business_id>/analytics/", include("apps.analytics.urls")),

    # Messages (customer inquiries)
    path("businesses/<uuid:business_id>/messages/", include("apps.messages.urls")),

    # Public storefront API (no auth, keyed by slug)
    path("store/", include("apps.businesses.storefront_urls")),
]
