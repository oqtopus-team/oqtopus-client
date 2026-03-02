"""Compatibility re-export for `oqtopus_client.errors`."""

from .services.errors import ResponseValidationError, UserApiError

__all__ = ["UserApiError", "ResponseValidationError"]
