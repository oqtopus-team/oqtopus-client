from __future__ import annotations

"""Error types raised by `oqtopus_client`."""

from typing import Any


class UserApiError(Exception):
    """Raised when the API returns a non-success status."""

    def __init__(self, status_code: int, message: str, payload: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.payload = payload
        super().__init__(f"HTTP {status_code}: {message}")


class ResponseValidationError(Exception):
    """Raised when a successful API response cannot be validated."""

    def __init__(self, message: str, payload: Any = None) -> None:
        self.message = message
        self.payload = payload
        super().__init__(message)
