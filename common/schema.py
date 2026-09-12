"""
drf-spectacular schema decorators for all views.

Since we use plain APIView (intentional — thin views, service layer),
we apply @extend_schema decorators directly on each view's methods
to give drf-spectacular the serializer/response information it needs.

This module is imported by each app's views file.
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

__all__ = ["extend_schema", "extend_schema_view", "OpenApiParameter", "OpenApiTypes"]
