"""
Public storefront URL patterns.
Mounted at /api/v1/store/ via api/v1/urls.py.

All routes are unauthenticated — keyed by business slug.

GET    {slug}/                          Storefront home (business profile)
GET    {slug}/products/                 Product list (active+available only)
GET    {slug}/products/{product_slug}/  Product detail by slug
GET    {slug}/categories/               Active categories
POST   {slug}/orders/                   Place order
POST   {slug}/messages/                 Contact form
"""
from django.urls import path
from apps.businesses.storefront_views import (
    StorefrontCategoryListView,
    StorefrontContactFormView,
    StorefrontHomeView,
    StorefrontOrderCreateView,
    StorefrontProductDetailView,
    StorefrontProductListView,
)

urlpatterns = [
    # Storefront home — business profile, theme, hero, contact
    path("<slug:slug>/", StorefrontHomeView.as_view(), name="storefront-home"),

    # Products
    path("<slug:slug>/products/", StorefrontProductListView.as_view(), name="storefront-products"),
    path(
        "<slug:slug>/products/<slug:product_slug>/",
        StorefrontProductDetailView.as_view(),
        name="storefront-product-detail",
    ),

    # Categories
    path("<slug:slug>/categories/", StorefrontCategoryListView.as_view(), name="storefront-categories"),

    # Commerce
    path("<slug:slug>/orders/", StorefrontOrderCreateView.as_view(), name="storefront-order-create"),
    path("<slug:slug>/messages/", StorefrontContactFormView.as_view(), name="storefront-contact"),
]
