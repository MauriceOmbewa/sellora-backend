"""
Business views — thin HTTP handlers.

Each view:
  1. Validates input via a serializer
  2. Calls a service or selector
  3. Returns a standardised response

No business logic, no ORM queries live here.
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.businesses.permissions import IsBusinessOwner
from apps.businesses.selectors import (
    get_business_by_id,
    get_business_by_slug,
    get_storefront_settings,
    get_user_businesses,
    get_business_settings,
)
from apps.businesses.serializers import (
    BusinessCreateSerializer,
    BusinessSerializer,
    BusinessSettingsSerializer,
    BusinessUpdateSerializer,
    StorefrontSettingsSerializer,
)
from apps.businesses.serializers.storefront import StorefrontSettingsUpdateSerializer
from apps.businesses.services import (
    create_business,
    publish_storefront,
    unpublish_storefront,
    update_business,
    update_business_settings,
    update_storefront_settings,
)
from common.exceptions import BusinessNotFound
from common.responses import created_response, no_content_response, success_response

logger = logging.getLogger("apps")


class BusinessListCreateView(APIView):
    """GET /businesses/ — list; POST /businesses/ — create (onboarding)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["businesses"], summary="List my businesses", responses={200: BusinessSerializer(many=True)})
    def get(self, request):
        businesses = get_user_businesses(request.user)
        serializer = BusinessSerializer(businesses, many=True)
        return success_response(data=serializer.data)

    @extend_schema(tags=["businesses"], summary="Create business (onboarding)", request=BusinessCreateSerializer, responses={201: BusinessSerializer})
    def post(self, request):
        serializer = BusinessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        business = create_business(
            owner=request.user,
            name=data["name"],
            category=data["category"],
            description=data.get("description", ""),
            motto=data.get("motto", ""),
            logo=data.get("logo", ""),
            contact=data.get("contact", {}),
            theme=data.get("theme", {}),
            hero=data.get("hero", {}),
            about_text=data.get("about_text", ""),
        )
        out = BusinessSerializer(business)
        return created_response(data=out.data, message="Business created successfully.")


class BusinessDetailView(APIView):
    """
    GET   /api/v1/businesses/{business_id}/    Retrieve a business.
    PATCH /api/v1/businesses/{business_id}/    Update a business.
    DELETE /api/v1/businesses/{business_id}/   Delete a business.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        # IsBusinessOwner already resolved & attached request.business
        serializer = BusinessSerializer(request.business)
        return success_response(data=serializer.data)

    def patch(self, request, business_id):
        serializer = BusinessUpdateSerializer(
            data=request.data,
            context={"business": request.business},
        )
        serializer.is_valid(raise_exception=True)

        business = update_business(request.business, **serializer.validated_data)
        out = BusinessSerializer(business)
        return success_response(data=out.data, message="Business updated successfully.")

    def delete(self, request, business_id):
        request.business.delete()
        return no_content_response()


class BusinessBySlugView(APIView):
    """
    GET /api/v1/businesses/by-slug/{slug}/

    Resolves a business slug to its full profile.
    Used by the frontend to initialise the storefront context.
    No authentication required — public endpoint.
    """
    permission_classes = []  # public

    def get(self, request, slug):
        business = get_business_by_slug(slug)
        if not business:
            raise BusinessNotFound()
        serializer = BusinessSerializer(business)
        return success_response(data=serializer.data)


class BusinessSettingsView(APIView):
    """
    GET /api/v1/businesses/{business_id}/settings/    Retrieve settings.
    PUT /api/v1/businesses/{business_id}/settings/    Update settings.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        settings = get_business_settings(request.business)
        if not settings:
            raise BusinessNotFound(detail="Business settings not found.")
        serializer = BusinessSettingsSerializer(settings)
        return success_response(data=serializer.data)

    def put(self, request, business_id):
        serializer = BusinessSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        settings = update_business_settings(
            request.business, **serializer.validated_data
        )
        out = BusinessSettingsSerializer(settings)
        return success_response(data=out.data, message="Settings updated.")


class StorefrontSettingsView(APIView):
    """
    GET  /api/v1/businesses/{business_id}/storefront/   Retrieve storefront config.
    PUT  /api/v1/businesses/{business_id}/storefront/   Save storefront changes.
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def get(self, request, business_id):
        sf = get_storefront_settings(request.business)
        if not sf:
            raise BusinessNotFound(detail="Storefront settings not found.")
        serializer = StorefrontSettingsSerializer(sf)
        return success_response(data=serializer.data)

    def put(self, request, business_id):
        serializer = StorefrontSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sf = update_storefront_settings(
            request.business, **serializer.validated_data
        )
        out = StorefrontSettingsSerializer(sf)
        return success_response(data=out.data, message="Storefront settings saved.")


class StorefrontPublishView(APIView):
    """
    POST /api/v1/businesses/{business_id}/storefront/publish/
    POST /api/v1/businesses/{business_id}/storefront/unpublish/
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id, action="publish"):
        if action == "unpublish":
            sf = unpublish_storefront(request.business)
            message = "Storefront taken offline."
        else:
            try:
                sf = publish_storefront(request.business)
            except ValueError as exc:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(str(exc))
            message = "Storefront is now live."

        out = StorefrontSettingsSerializer(sf)
        return success_response(data=out.data, message=message)
