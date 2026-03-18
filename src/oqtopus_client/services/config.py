"""Core module for oqtopus-client."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_CONFIG_PATH = object()
DEFAULT_SECTION = "default"
DEFAULT_BASE_URL_ENV = "OQTOPUS_BASE_URL"
DEFAULT_PROXY_ENV = "OQTOPUS_PROXY"
_ENV_PREFIX = "OQTOPUS"
_ENV_API_SEGMENT = "API"
_ENV_CREDENTIAL_SEGMENT = "TOKEN"
DEFAULT_API_TOKEN_ENV = (
    f"{_ENV_PREFIX}_{_ENV_API_SEGMENT}_{_ENV_CREDENTIAL_SEGMENT}"
)


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
        section: str = DEFAULT_SECTION,
        path: str | Path | object = _DEFAULT_CONFIG_PATH,
    ) -> OqtopusConfig:
        """Load configuration from an INI-style profile file.

        Args:
            section (Optional): INI section name to load. Defaults to ``default``.
            path (Optional): Config file path. When omitted, this method reads
                ``$XDG_CONFIG_HOME/oqtopus/config.ini`` if ``XDG_CONFIG_HOME`` is
                set; otherwise it reads ``~/.config/oqtopus/config.ini``.

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
            msg = "section should not be None."
            raise ValueError(msg)
        if path is None:
            msg = "path should not be None."
            raise ValueError(msg)

        if path is _DEFAULT_CONFIG_PATH:
            xdg_config_home = os.getenv("XDG_CONFIG_HOME")
            resolved_path = (
                Path(xdg_config_home, "oqtopus", "config.ini")
                if xdg_config_home
                else Path("~/.config/oqtopus/config.ini")
            )
        else:
            resolved_path = Path(os.path.expandvars(str(path))).expanduser()
        expanded = resolved_path.expanduser()
        parser = configparser.ConfigParser()
        parser.read(expanded, encoding="utf-8")
        if section not in parser:
            msg = f"Section '{section}' not found in config file: {expanded}"
            raise ValueError(msg)

        cfg = parser[section]
        base_url = cfg.get("base_url")
        if not base_url:
            msg = f"Section '{section}' in {expanded} must define 'base_url'."
            raise ValueError(msg)

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
        base_url_env: str = DEFAULT_BASE_URL_ENV,
        proxy_env: str = DEFAULT_PROXY_ENV,
        api_token_env: str = DEFAULT_API_TOKEN_ENV,
    ) -> OqtopusConfig:
        """Load configuration from environment variables.

        Args:
            base_url_env (Optional): Environment variable name used for the API
                base URL. Defaults to ``OQTOPUS_BASE_URL``.
            proxy_env (Optional): Environment variable name used for the proxy
                URL. Defaults to ``OQTOPUS_PROXY``.
            api_token_env (Optional): Environment variable name used for the API
                token. Defaults to ``OQTOPUS_API_TOKEN``.

        Returns:
            Configuration loaded from environment variables.

        Raises:
            ValueError: If the base URL environment variable is not set.

        """
        base_url = os.getenv(base_url_env)
        if not base_url:
            msg = f"Environment variable {base_url_env} is required."
            raise ValueError(msg)

        api_token = os.getenv(api_token_env)
        return cls(
            base_url=base_url,
            api_token=api_token,
            proxy=os.getenv(proxy_env),
        )
