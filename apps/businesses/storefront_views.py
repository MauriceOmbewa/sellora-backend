"""
Public storefront views.

All views are unauthenticated (permission_classes = []).
All views use StorefrontBusinessMixin to resolve the slug → business.

URL structure: /api/v1/store/{slug}/...
"""
import logging
from decimal import Decimal

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.businesses.serializers import BusinessSerializer
from apps.businesses.storefront_utils import StorefrontBusinessMixin
from apps.categories.selectors import get_categories_for_business
from apps.categories.serializers import CategorySerializer
from apps.messages.serializers import ContactFormSerializer
from apps.messages.services import create_message
from apps.orders.serializers import OrderCreateSerializer, OrderSerializer
from apps.orders.services import create_order
from apps.products.selectors import get_product_by_slug, get_storefront_products
from apps.products.serializers import ProductPublicSerializer
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from common.responses import created_response, success_response

logger = logging.getLogger("apps")


class StorefrontHomeView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/

    Returns the full business profile for the storefront home page.
    Includes theme, hero, contact, social links, storefront settings,
    and delivery configuration.
    Does NOT include costPrice or any private fields.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        business = self.storefront_business
        data = BusinessSerializer(business).data

        # Append delivery settings so the frontend can use the real fee
        try:
            s = business.settings
            data["delivery_settings"] = {
                "delivery_enabled":        s.delivery_enabled,
                "pickup_enabled":          s.pickup_enabled,
                "delivery_fee":            str(s.delivery_fee),
                "free_delivery_threshold": str(s.free_delivery_threshold),
            }
        except Exception:
            data["delivery_settings"] = {
                "delivery_enabled":        True,
                "pickup_enabled":          True,
                "delivery_fee":            "300",
                "free_delivery_threshold": "10000",
            }

        return success_response(data=data)


class StorefrontProductListView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/products/

    Returns active + available products for the storefront shop page.
    costPrice is NEVER included (ProductPublicSerializer).

    Query params:
        category_id  — filter by category UUID
        search       — partial name match
        sort         — featured | newest | price-asc | price-desc | best-selling
        page, page_size
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        business = self.storefront_business
        products = get_storefront_products(
            business,
            category_id=request.query_params.get("category_id"),
            search=request.query_params.get("search"),
            sort=request.query_params.get("sort"),
        )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(products, request)
        return paginator.get_paginated_response(
            ProductPublicSerializer(page, many=True).data
        )


class StorefrontProductDetailView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/products/{product_slug}/

    Returns a single product by its slug.
    Used by the storefront product detail page.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug, product_slug):
        business = self.storefront_business
        product = get_product_by_slug(product_slug, business)
        if not product:
            raise ResourceNotFound("Product not found.")
        return success_response(data=ProductPublicSerializer(product).data)


class StorefrontCategoryListView(StorefrontBusinessMixin, APIView):
    """
    GET /api/v1/store/{slug}/categories/

    Returns active categories for storefront filtering.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        business = self.storefront_business
        categories = get_categories_for_business(business, active_only=True)
        return success_response(
            data=CategorySerializer(categories, many=True).data
        )


class StorefrontOrderCreateView(StorefrontBusinessMixin, APIView):
    """
    POST /api/v1/store/{slug}/orders/

    Place an order from the storefront checkout page.
    No authentication required.

    Request body matches OrderCreateSerializer — same as dashboard,
    but channel defaults to 'online' and is not changeable from
    the storefront (frontend always sends online orders).

    On success:
      - Order created with status=new
      - Stock decremented
      - Customer auto-created/upserted by phone
      - New order email notification dispatched (if enabled)
    """
    permission_classes = [AllowAny]

    def post(self, request, slug):
        business = self.storefront_business

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Storefront orders are always 'online' channel
        data["channel"] = "online"

        # fulfillment_type from request: 'delivery' (default) or 'pickup'
        fulfillment_type = request.data.get("fulfillment_type", "delivery")
        is_pickup = fulfillment_type == "pickup"

        # For pickup orders, delivery fee is zero regardless of subtotal.
        # For delivery, let create_order read from business settings.
        custom_delivery_fee = Decimal("0") if is_pickup else None

        # If business has per-business settings, pass them as custom_delivery_fee
        # only if this is a delivery order (pickup already handled above).
        if not is_pickup:
            try:
                s = business.settings
                custom_delivery_fee = None   # let create_order use settings
            except Exception:
                pass

        try:
            order = create_order(
                business,
                customer_name=data["customer_name"],
                customer_phone=data["customer_phone"],
                customer_email=data.get("customer_email", ""),
                delivery_address=data.get("delivery_address", ""),
                order_notes=data.get("order_notes", ""),
                payment_method=data["payment_method"],
                channel="online",
                items=data["items"],
                discount=data.get("discount", Decimal("0")),
                custom_delivery_fee=custom_delivery_fee,
                fulfillment_type=fulfillment_type,
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))

        # Return minimal order confirmation — no sensitive business data
        return created_response(
            data={
                "id": str(order.id),
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "total": str(order.total),
                "delivery_fee": str(order.delivery_fee),
                "subtotal": str(order.subtotal),
                "payment_method": order.payment_method,
                "status": order.status,
            },
            message="Order placed successfully!"
        )


class StorefrontContactFormView(StorefrontBusinessMixin, APIView):
    """
    POST /api/v1/store/{slug}/messages/

    Submit a contact form message from the storefront.
    No authentication required.

    On success:
      - CustomerMessage created with status=unread
      - Email notification dispatched to business owner (if enabled)
    """
    permission_classes = [AllowAny]

    def post(self, request, slug):
        business = self.storefront_business

        serializer = ContactFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        create_message(
            business,
            sender_name=data["sender_name"],
            sender_phone=data.get("sender_phone", ""),
            sender_email=data.get("sender_email", ""),
            subject=data.get("subject", ""),
            body=data["body"],
            channel=data.get("channel", "contact_form"),
        )

        return created_response(
            data=None,
            message="Your message has been sent. We'll be in touch soon!"
        )
