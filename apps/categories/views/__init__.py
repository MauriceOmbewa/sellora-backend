"""
Category views.

Mounted at /api/v1/businesses/{business_id}/categories/
All views require IsAuthenticated + IsBusinessOwner.
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.categories.selectors import get_categories_for_business, get_category_by_id
from apps.categories.serializers import (
    CategoryCreateSerializer,
    CategorySerializer,
    CategoryUpdateSerializer,
)
from apps.categories.services import create_category, delete_category, update_category
from common.exceptions import ResourceNotFound
from common.responses import created_response, no_content_response, success_response

logger = logging.getLogger("apps")


class CategoryListCreateView(APIView):
    """
    GET  /api/v1/businesses/{business_id}/categories/   List categories.
    POST /api/v1/businesses/{business_id}/categories/   Create a category.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        # ?active=true to filter active only (used by storefront)
        active_only = request.query_params.get("active", "").lower() == "true"
        categories = get_categories_for_business(request.business, active_only=active_only)
        serializer = CategorySerializer(categories, many=True)
        return success_response(data=serializer.data)

    def post(self, request, business_id):
        serializer = CategoryCreateSerializer(
            data=request.data,
            context={"business": request.business},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category = create_category(
            business=request.business,
            name=data["name"],
            description=data.get("description", ""),
            image_url=data.get("image_url", ""),
            slug=data.get("slug") or None,
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
        )
        out = CategorySerializer(category)
        return created_response(data=out.data, message="Category created.")


class CategoryDetailView(APIView):
    """
    GET    /api/v1/businesses/{business_id}/categories/{category_id}/
    PATCH  /api/v1/businesses/{business_id}/categories/{category_id}/
    DELETE /api/v1/businesses/{business_id}/categories/{category_id}/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_category_or_404(self, category_id, business):
        category = get_category_by_id(category_id, business=business)
        if not category:
            raise ResourceNotFound("Category not found.")
        return category

    def get(self, request, business_id, category_id):
        category = self._get_category_or_404(category_id, request.business)
        return success_response(data=CategorySerializer(category).data)

    def patch(self, request, business_id, category_id):
        category = self._get_category_or_404(category_id, request.business)
        serializer = CategoryUpdateSerializer(
            data=request.data,
            context={"business": request.business, "category": category},
        )
        serializer.is_valid(raise_exception=True)
        category = update_category(category, **serializer.validated_data)
        return success_response(data=CategorySerializer(category).data)

    def delete(self, request, business_id, category_id):
        category = self._get_category_or_404(category_id, request.business)
        delete_category(category)
        return no_content_response()
