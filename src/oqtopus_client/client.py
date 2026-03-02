"""Compatibility re-export for `oqtopus_client.client`."""

from importlib.metadata import PackageNotFoundError, version

from .config import OqtopusConfig
from .services.client import OqtopusClient, _AsyncOqtopusClient, _shutdown_shared_runtime

PACKAGE_NAME = "oqtopus-client"


def _resolve_user_agent() -> str:
    """Resolve default User-Agent value for compatibility imports."""
    try:
        package_version = version(PACKAGE_NAME)
    except PackageNotFoundError:
        package_version = "unknown"
    return f"{PACKAGE_NAME}/{package_version}"

__all__ = [
    "OqtopusClient",
    "OqtopusConfig",
    "version",
    "_AsyncOqtopusClient",
    "_shutdown_shared_runtime",
    "_resolve_user_agent",
]
