"""Core module for oqtopus-client."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OqtopusConfig:
    """Shared client configuration bundle.

    Attributes:
        base_url: OQTOPUS API base URL.
        api_token: API token string.
        timeout: HTTP request timeout seconds.
        retry_max_attempts: Max retry attempts for retryable requests.
        retry_backoff_seconds: Exponential backoff base seconds.
        retry_status_codes: HTTP status codes treated as retryable.
        retry_methods: HTTP methods treated as retryable.

    """

    base_url: str
    api_token: str | None = None
    proxy: str | None = None
    timeout: float = 30.0
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.2
    retry_status_codes: frozenset[int] | None = None
    retry_methods: frozenset[str] | None = None

    @classmethod
    def from_file(
        cls,
        section: str = "default",
        path: str | Path = "~/.config/oqtopus/config.ini",
    ) -> OqtopusConfig:
        """Load configuration from an INI-style profile file.

        Example:
            OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))

        Returns:
            Configuration loaded from the requested profile.

        Raises:
            ValueError: If ``section`` or ``path`` is invalid, or if the profile is
                missing required values.

        """
        if os.getenv("OQTOPUS_ENV") == "sse_container":
            # Same behavior as quri-parts-oqtopus: config file is not required
            # inside the SSE container runtime.
            return cls(base_url="", api_token="")

        if section is None:
            raise ValueError("section should not be None.")
        if path is None:
            raise ValueError("path should not be None.")

        expanded = Path(os.path.expandvars(str(path))).expanduser()
        parser = configparser.ConfigParser()
        parser.read(expanded, encoding="utf-8")
        if section not in parser:
            raise ValueError(
                f"Section '{section}' not found in config file: {expanded}"
            )

        cfg = parser[section]
        base_url = cfg.get("base_url")
        if not base_url:
            raise ValueError(
                f"Section '{section}' in {expanded} must define 'base_url'.",
            )

        api_token = cfg.get("api_token")
        proxy = cfg.get("proxy")
        timeout = cfg.getfloat("timeout", fallback=30.0)

        return cls(
            base_url=base_url,
            api_token=api_token,
            proxy=proxy,
            timeout=timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        base_url_env: str = "OQTOPUS_BASE_URL",
        proxy_env: str = "OQTOPUS_PROXY",
        api_token_env: str = "OQTOPUS_API_TOKEN",
    ) -> OqtopusConfig:
        """Load configuration from environment variables.

        Returns:
            Configuration loaded from environment variables.

        Raises:
            ValueError: If the base URL environment variable is not set.

        """
        base_url = os.getenv(base_url_env)
        if not base_url:
            raise ValueError(f"Environment variable {base_url_env} is required.")

        api_token = os.getenv(api_token_env)
        return cls(
            base_url=base_url,
            api_token=api_token,
            proxy=os.getenv(proxy_env),
        )
