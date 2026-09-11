"""
Tenant middleware.

Resolves the current business/tenant from the URL and attaches it to the
request object as `request.business`.

Two resolution strategies:
  1. Dashboard routes:  /api/v1/businesses/{business_id}/...
     → looks up Business by UUID primary key, verifies the user is the owner
  2. Storefront routes: /api/v1/store/{slug}/...
     → looks up Business by slug (public, no auth required)

If the business_id / slug is not in the URL (e.g. /api/v1/auth/ routes),
request.business is set to None and the middleware passes through.
"""
import re
import uuid
import logging

logger = logging.getLogger("apps")

# Patterns that carry a business context
_BUSINESS_ID_PATTERN = re.compile(r"/businesses/([0-9a-f-]{36})/")
_STORE_SLUG_PATTERN = re.compile(r"/store/([^/]+)/")


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.business = None  # default: no tenant context

        path = request.path

        # ── Dashboard route ──────────────────────────────────────────────────
        match = _BUSINESS_ID_PATTERN.search(path)
        if match:
            try:
                business_id = uuid.UUID(match.group(1))
                request._tenant_business_id = business_id
                # Full Business object is attached lazily by the permission
                # class (IsBusinessOwner) to avoid a DB hit on every request,
                # including unauthenticated ones that will 401 anyway.
            except ValueError:
                pass
            return self.get_response(request)

        # ── Public storefront route ──────────────────────────────────────────
        match = _STORE_SLUG_PATTERN.search(path)
        if match:
            request._tenant_slug = match.group(1)
            # Business resolution deferred to the storefront views/permissions
            return self.get_response(request)

        return self.get_response(request)
