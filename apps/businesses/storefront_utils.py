"""
Storefront utility — resolve a business slug from a URL kwarg.

Used by all public storefront views as a mixin.
Raises 404 if the slug doesn't match an active, published business.
"""
from rest_framework.exceptions import NotFound


class StorefrontBusinessMixin:
    """
    Mixin for public storefront views.

    Resolves the `slug` URL kwarg → Business and attaches it to
    `self.storefront_business` before the view handler runs.

    Raises 404:
      - Business not found or not active
      - Storefront is not published (is_published=False)

    Views inherit this mixin and access the business via:
        business = self.storefront_business
    """

    _storefront_business = None

    @property
    def storefront_business(self):
        if self._storefront_business is None:
            self._storefront_business = self._resolve_storefront_business()
        return self._storefront_business

    def _resolve_storefront_business(self):
        from apps.businesses.selectors import get_business_by_slug
        from apps.businesses.models import StorefrontSettings

        slug = self.kwargs.get("slug")
        if not slug:
            raise NotFound("Store not found.")

        business = get_business_by_slug(slug)
        if not business:
            raise NotFound("Store not found.")

        # Check storefront is published
        try:
            sf_settings = business.storefront_settings
            if not sf_settings.is_published:
                raise NotFound("This store is not available.")
        except StorefrontSettings.DoesNotExist:
            raise NotFound("This store is not available.")

        return business

    def initial(self, request, *args, **kwargs):
        """Override DRF initial to resolve business before dispatch."""
        super().initial(request, *args, **kwargs)
        # Eagerly resolve so any 404 fires before the handler runs
        _ = self.storefront_business
