"""
Category URL patterns.
Mounted at /api/v1/businesses/{business_id}/categories/

GET    /  — list
POST   /  — create
GET    /{category_id}/ — detail
PATCH  /{category_id}/ — update
DELETE /{category_id}/ — delete
"""
from django.urls import path
from apps.categories.views import CategoryDetailView, CategoryListCreateView

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="category-list-create"),
    path("<uuid:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
]
