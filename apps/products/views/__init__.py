"""
Product views — dashboard (authenticated) only.
Public storefront product views live in apps/businesses/storefront_urls.py (Step 17).
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.categories.selectors import get_category_by_id
from apps.products.selectors import get_product_by_id, get_products_for_business
from apps.products.serializers import (
    ProductCreateSerializer,
    ProductSerializer,
    ProductUpdateSerializer,
)
from apps.products.services import archive_product, create_product, update_product
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import created_response, no_content_response, success_response

logger = logging.getLogger("apps")


class ProductListCreateView(APIView):
    """
    GET  /api/v1/businesses/{business_id}/products/
    POST /api/v1/businesses/{business_id}/products/

    Query params for GET:
        status      — filter by status (active/draft/archived)
        category_id — filter by category UUID
        search      — partial name match
        page        — page number (default 1)
        page_size   — results per page (default 20, max 100)
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        products = get_products_for_business(
            request.business,
            status=request.query_params.get("status"),
            category_id=request.query_params.get("category_id"),
            search=request.query_params.get("search"),
        )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_id):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve category FK if provided
        category = None
        category_id = data.pop("category_id", None)
        if category_id:
            category = get_category_by_id(category_id, business=request.business)
            if not category:
                raise ResourceNotFound("Category not found.")

        product = create_product(
            business=request.business,
            category=category,
            **data,
        )
        return created_response(
            data=ProductSerializer(product).data,
            message="Product created."
        )


class ProductDetailView(APIView):
    """
    GET    /api/v1/businesses/{business_id}/products/{product_id}/
    PATCH  /api/v1/businesses/{business_id}/products/{product_id}/
    DELETE /api/v1/businesses/{business_id}/products/{product_id}/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_or_404(self, product_id, business):
        product = get_product_by_id(product_id, business=business)
        if not product:
            raise ResourceNotFound("Product not found.")
        return product

    def get(self, request, business_id, product_id):
        product = self._get_or_404(product_id, request.business)
        return success_response(data=ProductSerializer(product).data)

    def patch(self, request, business_id, product_id):
        product = self._get_or_404(product_id, request.business)
        serializer = ProductUpdateSerializer(
            data=request.data,
            context={"business": request.business, "product": product},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve category FK if provided in update
        category_id = data.pop("category_id", None)
        if "category_id" in request.data:
            category = None
            if category_id:
                category = get_category_by_id(category_id, business=request.business)
                if not category:
                    raise ResourceNotFound("Category not found.")
            data["category"] = category

        product = update_product(product, **data)
        return success_response(
            data=ProductSerializer(product).data,
            message="Product updated."
        )

    def delete(self, request, business_id, product_id):
        product = self._get_or_404(product_id, request.business)
        archive_product(product)  # soft delete — archive rather than destroy
        return no_content_response()
