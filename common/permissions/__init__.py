"""
Shared permission classes used across all apps.
Import from here rather than from individual app permission files.
"""
from apps.businesses.permissions import IsBusinessOwner

__all__ = ["IsBusinessOwner"]
