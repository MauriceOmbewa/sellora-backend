"""
Business URL patterns.

Mounted at /api/v1/businesses/ via api/v1/urls.py.

Full paths:
    GET    /api/v1/businesses/                                  List user's businesses
    POST   /api/v1/businesses/                                  Create business (onboarding)
    GET    /api/v1/businesses/by-slug/{slug}/                   Resolve slug → business (public)
    GET    /api/v1/businesses/{business_id}/                    Get business detail
    PATCH  /api/v1/businesses/{business_id}/                    Update business
    DELETE /api/v1/businesses/{business_id}/                    Delete business
    GET    /api/v1/businesses/{business_id}/settings/           Get business settings
    PUT    /api/v1/businesses/{business_id}/settings/           Update business settings
    GET    /api/v1/businesses/{business_id}/storefront/         Get storefront settings
    PUT    /api/v1/businesses/{business_id}/storefront/         Save storefront settings
    POST   /api/v1/businesses/{business_id}/storefront/publish/ Publish storefront
    POST   /api/v1/businesses/{business_id}/storefront/unpublish/ Unpublish storefront
"""
from django.urls import path

from apps.businesses.views import (
    BusinessBySlugView,
    BusinessDetailView,
    BusinessListCreateView,
    BusinessSettingsView,
    StorefrontPublishView,
    StorefrontSettingsView,
)

urlpatterns = [
    # ── Collection ────────────────────────────────────────────────────────────
    path("", BusinessListCreateView.as_view(), name="business-list-create"),

    # ── Public slug resolution (before the UUID pattern to avoid conflict) ────
    path("by-slug/<slug:slug>/", BusinessBySlugView.as_view(), name="business-by-slug"),

    # ── Single business ───────────────────────────────────────────────────────
    path("<uuid:business_id>/", BusinessDetailView.as_view(), name="business-detail"),

    # ── Settings ──────────────────────────────────────────────────────────────
    path("<uuid:business_id>/settings/", BusinessSettingsView.as_view(), name="business-settings"),

    # ── Storefront ────────────────────────────────────────────────────────────
    path(
        "<uuid:business_id>/storefront/",
        StorefrontSettingsView.as_view(),
        name="business-storefront-settings",
    ),
    path(
        "<uuid:business_id>/storefront/publish/",
        StorefrontPublishView.as_view(),
        {"action": "publish"},
        name="business-storefront-publish",
    ),
    path(
        "<uuid:business_id>/storefront/unpublish/",
        StorefrontPublishView.as_view(),
        {"action": "unpublish"},
        name="business-storefront-unpublish",
    ),
]
