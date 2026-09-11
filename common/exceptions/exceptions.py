"""
Custom application exceptions.

All exceptions inherit from DRF's APIException so they are caught by the
custom_exception_handler and serialized into the standard response format.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ResourceNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class BusinessNotFound(ResourceNotFound):
    default_detail = "Business not found."
    default_code = "business_not_found"


class NotBusinessOwner(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to access this business."
    default_code = "not_business_owner"


class InvalidGoogleToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid or expired Google token."
    default_code = "invalid_google_token"


class ValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input."
    default_code = "validation_error"


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with the current state of the resource."
    default_code = "conflict"
