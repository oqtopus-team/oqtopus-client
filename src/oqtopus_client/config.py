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
        api_token_file: Path to a token file (mutually exclusive with ``api_token``).
        timeout: HTTP request timeout seconds.
        retry_max_attempts: Max retry attempts for retryable requests.
        retry_backoff_seconds: Exponential backoff base seconds.
        retry_status_codes: HTTP status codes treated as retryable.
        retry_methods: HTTP methods treated as retryable.
    """

    base_url: str
    api_token: str | None = None
    api_token_file: str | Path | None = None
    timeout: float = 30.0
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.2
    retry_status_codes: frozenset[int] | None = None
    retry_methods: frozenset[str] | None = None

    @classmethod
    def from_file(
        cls,
        section: str = "default",
        path: str | Path = "~/.oqtopus",
    ) -> "OqtopusConfig":
        """Load configuration from an INI-style profile file.

        Example:
            OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))
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
            raise ValueError(f"Section '{section}' not found in config file: {expanded}")

        cfg = parser[section]
        base_url = cfg.get("base_url") or cfg.get("url")
        if not base_url:
            raise ValueError(
                f"Section '{section}' in {expanded} must define 'base_url' or 'url'."
            )

        api_token = cfg.get("api_token")
        api_token_file = cfg.get("api_token_file")
        timeout = cfg.getfloat("timeout", fallback=30.0)

        return cls(
            base_url=base_url,
            api_token=api_token,
            api_token_file=Path(api_token_file) if api_token_file else None,
            timeout=timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        base_url_env: str = "OQTOPUS_BASE_URL",
        api_token_env: str = "OQTOPUS_API_TOKEN",
        api_token_file_env: str = "OQTOPUS_API_TOKEN_FILE",
    ) -> "OqtopusConfig":
        """Load configuration from environment variables."""
        base_url = os.getenv(base_url_env)
        if not base_url:
            raise ValueError(f"Environment variable {base_url_env} is required.")

        api_token = os.getenv(api_token_env)
        api_token_file_value = os.getenv(api_token_file_env)
        return cls(
            base_url=base_url,
            api_token=api_token,
            api_token_file=Path(api_token_file_value) if api_token_file_value else None,
        )
