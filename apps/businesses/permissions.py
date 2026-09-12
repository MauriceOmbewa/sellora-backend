"""
Business permissions.

IsBusinessOwner is the central permission class used across ALL apps
that operate on business-scoped resources (products, orders, customers, etc.).

It is placed here in the businesses app because the Business model lives here,
but it is imported and reused by every other app's views.
"""
import logging

from rest_framework.permissions import BasePermission

from apps.businesses.selectors import get_business_by_id

logger = logging.getLogger("apps")


class IsBusinessOwner(BasePermission):
    """
    Grants access only if the authenticated user owns the business
    identified by `business_id` in the URL kwargs.

    Also attaches `request.business` for use in the view — so views
    never need to re-query the database for the business object.

    Usage in any view:
        permission_classes = [IsAuthenticated, IsBusinessOwner]

    The view receives the resolved business via:
        business = request.business
    """

    message = "You do not have permission to access this business."

    def has_permission(self, request, view):
        # Must be authenticated first
        if not request.user or not request.user.is_authenticated:
            return False

        # Get business_id from URL — set by the URL pattern as <uuid:business_id>
        business_id = view.kwargs.get("business_id")
        if not business_id:
            # No business_id in URL — this permission doesn't apply here
            return True

        business = get_business_by_id(business_id)

        if business is None:
            self.message = "Business not found."
            return False

        if business.owner_id != request.user.id:
            logger.warning(
                "User %s attempted to access business %s owned by %s",
                request.user.id,
                business_id,
                business.owner_id,
            )
            return False

        # Attach to request so views don't re-query
        request.business = business
        return True
