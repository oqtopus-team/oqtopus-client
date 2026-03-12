"""Core module for oqtopus-client."""

from __future__ import annotations


class UserApiError(Exception):
    """Raised when the API returns a non-success status."""

    def __init__(
        self,
        status_code: int,
        message: str,
        payload: object | None = None,
    ) -> None:
        """Create an API error with status code, message, and optional payload."""
        self.status_code = status_code
        self.message = message
        self.payload = payload
        super().__init__(f"HTTP {status_code}: {message}")


class ResponseValidationError(Exception):
    """Raised when a successful API response cannot be validated."""

    def __init__(self, message: str, payload: object | None = None) -> None:
        """Create a response validation error with optional raw payload."""
        self.message = message
        self.payload = payload
        super().__init__(message)
