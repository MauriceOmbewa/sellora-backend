"""Customer views — read-heavy, minimal writes."""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.businesses.permissions import IsBusinessOwner
from apps.customers.selectors import get_customer_by_id, get_customers_for_business
from apps.customers.serializers import CustomerSerializer, CustomerUpdateSerializer
from apps.customers.services import update_customer
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import success_response

logger = logging.getLogger("apps")


class CustomerListView(APIView):
    """
    GET /api/v1/businesses/{business_id}/customers/
    Query params: search, status, page, page_size
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        customers = get_customers_for_business(
            request.business,
            search=request.query_params.get("search"),
            status=request.query_params.get("status"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(customers, request)
        return paginator.get_paginated_response(
            CustomerSerializer(page, many=True).data
        )


class CustomerDetailView(APIView):
    """
    GET   /api/v1/businesses/{business_id}/customers/{customer_id}/
    PATCH /api/v1/businesses/{business_id}/customers/{customer_id}/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def _get_or_404(self, customer_id, business):
        customer = get_customer_by_id(customer_id, business=business)
        if not customer:
            raise ResourceNotFound("Customer not found.")
        return customer

    def get(self, request, business_id, customer_id):
        customer = self._get_or_404(customer_id, request.business)
        # Include recent orders — orders app queried separately by frontend
        return success_response(data=CustomerSerializer(customer).data)

    def patch(self, request, business_id, customer_id):
        customer = self._get_or_404(customer_id, request.business)
        serializer = CustomerUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = update_customer(customer, **serializer.validated_data)
        return success_response(
            data=CustomerSerializer(customer).data,
            message="Customer updated."
        )
