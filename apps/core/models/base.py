"""
Abstract base models shared across all apps.
"""
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Adds created_at and updated_at to any model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    """
    Primary base model for all Sellora entities.

    Uses UUID as primary key — avoids sequential integer leakage
    and plays well with multi-tenant architecture.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.id)
