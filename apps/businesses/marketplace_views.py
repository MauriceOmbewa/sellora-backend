"""
Public marketplace views — cross-vendor product discovery.

Endpoints:
    GET /api/v1/marketplace/products/          All products across published stores
    GET /api/v1/marketplace/products/{id}/     Single product with full vendor details

Both are completely unauthenticated (AllowAny). cost_price is never exposed.

Query params for the list endpoint:
    search      partial name match (case-insensitive)
    category    partial category name match
    sort        featured | newest | price-asc | price-desc | best-selling
    featured    true/false — filter to featured-only products
    page        page number (default 1)
    page_size   results per page (default 24, max 100)
"""
import logging

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.products.selectors import get_marketplace_products, get_marketplace_product_by_id
from apps.products.serializers import MarketplaceProductSerializer
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import success_response

logger = logging.getLogger("apps")


class MarketplaceProductListView(APIView):
    """
    GET /api/v1/marketplace/products/

    Returns products from all active, published storefronts on the platform.
    Supports search, category filter, sort, and pagination.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        search   = request.query_params.get("search")
        category = request.query_params.get("category")
        sort     = request.query_params.get("sort")
        featured = request.query_params.get("featured", "").lower() == "true"

        products = get_marketplace_products(
            search=search,
            sort=sort,
            category=category,
            featured=featured,
        )

        paginator = StandardResultsPagination()
        # Allow caller to override page_size up to max (set on paginator)
        page = paginator.paginate_queryset(products, request)
        serializer = MarketplaceProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MarketplaceProductDetailView(APIView):
    """
    GET /api/v1/marketplace/products/{product_id}/

    Returns a single product with full vendor identity fields.
    Returns 404 if the product doesn't exist, is unpublished,
    belongs to an inactive business, or is not available.
    """
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        product = get_marketplace_product_by_id(product_id)
        if not product:
            raise ResourceNotFound("Product not found.")
        return success_response(data=MarketplaceProductSerializer(product).data)
