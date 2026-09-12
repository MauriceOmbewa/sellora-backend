"""
Business domain validators.
Called from serializers before data reaches the service layer.
"""
import re

from rest_framework.exceptions import ValidationError


def validate_slug(value: str) -> str:
    """Ensure a slug contains only lowercase letters, digits, and hyphens."""
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
        raise ValidationError(
            "Slug may only contain lowercase letters, digits, and hyphens, "
            "and cannot start or end with a hyphen."
        )
    if len(value) < 3:
        raise ValidationError("Slug must be at least 3 characters long.")
    if len(value) > 100:
        raise ValidationError("Slug must be 100 characters or fewer.")
    return value


def validate_hex_color(value: str) -> str:
    """Ensure a value is a valid CSS hex color like #7C3AED."""
    if not re.match(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", value):
        raise ValidationError(f"'{value}' is not a valid hex color (e.g. #7C3AED).")
    return value


def validate_theme(theme: dict) -> dict:
    """Validate that theme keys are present and values are valid hex colors."""
    required_keys = [
        "primaryColor", "primaryHover", "accentColor",
        "backgroundColor", "textColor",
    ]
    for key in required_keys:
        if key in theme:
            validate_hex_color(theme[key])
    return theme
