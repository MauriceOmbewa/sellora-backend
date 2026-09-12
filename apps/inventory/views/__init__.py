"""Inventory views."""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.inventory.selectors import get_inventory_for_business, get_stock_adjustments_for_business
from apps.inventory.serializers import (
    InventoryItemSerializer,
    StockAdjustInputSerializer,
    StockAdjustmentSerializer,
)
from apps.products.selectors import get_product_by_id
from apps.products.services import adjust_stock
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import created_response, success_response

logger = logging.getLogger("apps")


class InventoryListView(APIView):
    """
    GET /api/v1/businesses/{business_id}/inventory/
    Query params: low_stock=true, page, page_size
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        low_stock_only = request.query_params.get("low_stock", "").lower() == "true"
        items = get_inventory_for_business(
            request.business, low_stock_only=low_stock_only
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(items, request)
        return paginator.get_paginated_response(
            InventoryItemSerializer(page, many=True).data
        )


class StockAdjustView(APIView):
    """
    POST /api/v1/businesses/{business_id}/inventory/adjust/
    Body: { "product_id": uuid, "quantity_delta": int, "reason": str }
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id):
        serializer = StockAdjustInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product = get_product_by_id(data["product_id"], business=request.business)
        if not product:
            raise ResourceNotFound("Product not found in this business.")

        try:
            product = adjust_stock(
                product,
                quantity_delta=data["quantity_delta"],
                reason=data.get("reason", ""),
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))

        return created_response(
            data=InventoryItemSerializer(product).data,
            message="Stock adjusted successfully."
        )


class StockAdjustmentHistoryView(APIView):
    """
    GET /api/v1/businesses/{business_id}/inventory/history/
    Returns all stock adjustments across the business.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        adjustments = get_stock_adjustments_for_business(request.business)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(adjustments, request)
        return paginator.get_paginated_response(
            StockAdjustmentSerializer(page, many=True).data
        )
