"""
Public marketplace URL patterns.
Mounted at /api/v1/marketplace/ via api/v1/urls.py.

GET  products/           All products across active published storefronts
GET  products/{id}/      Single product with vendor details
"""
from django.urls import path
from apps.businesses.marketplace_views import (
    MarketplaceProductDetailView,
    MarketplaceProductListView,
)

urlpatterns = [
    path("products/",         MarketplaceProductListView.as_view(),  name="marketplace-products"),
    path("products/<uuid:product_id>/", MarketplaceProductDetailView.as_view(), name="marketplace-product-detail"),
]
