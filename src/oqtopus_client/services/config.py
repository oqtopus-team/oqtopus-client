"""Core module for oqtopus-client."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_CONFIG_PATH = object()
DEFAULT_SECTION = "default"
DEFAULT_URL_ENV = "OQTOPUS_URL"
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
        url: OQTOPUS API URL.
        base_url: Backward-compatible alias for ``url``.
        api_token: API token string. Excluded from ``repr()``.
        proxy: Proxy URL. Excluded from ``repr()``.
        timeout: HTTP request timeout seconds.
        retry_max_attempts: Max retry attempts for retryable requests.
        retry_backoff_seconds: Exponential backoff base seconds.
        retry_status_codes: HTTP status codes treated as retryable.
        retry_methods: HTTP methods treated as retryable.

    """

    url: str
    api_token: str | None = field(default=None, repr=False)
    proxy: str | None = field(default=None, repr=False)
    timeout: float = 30.0
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.2
    retry_status_codes: frozenset[int] | None = None
    retry_methods: frozenset[str] | None = None

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        url: str | None = None,
        api_token: str | None = None,
        proxy: str | None = None,
        timeout: float = 30.0,
        retry_max_attempts: int = 3,
        retry_backoff_seconds: float = 0.2,
        retry_status_codes: frozenset[int] | None = None,
        retry_methods: frozenset[str] | None = None,
        *,
        base_url: str | None = None,
    ) -> None:
        """Initialize an OQTOPUS configuration.

        Args:
            url: OQTOPUS API URL.
            api_token: API token string.
            proxy: Proxy URL.
            timeout: HTTP request timeout seconds.
            retry_max_attempts: Max retry attempts for retryable requests.
            retry_backoff_seconds: Exponential backoff base seconds.
            retry_status_codes: HTTP status codes treated as retryable.
            retry_methods: HTTP methods treated as retryable.
            base_url: Backward-compatible alias for ``url``.

        Raises:
            ValueError: If neither URL argument is provided or they conflict.

        """
        if url is not None and base_url is not None and url != base_url:
            msg = "url and base_url must match when both are provided."
            raise ValueError(msg)
        resolved_url = url if url is not None else base_url
        if resolved_url is None:
            msg = "url (or base_url) is required."
            raise ValueError(msg)

        object.__setattr__(self, "url", resolved_url)
        object.__setattr__(self, "api_token", api_token)
        object.__setattr__(self, "proxy", proxy)
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "retry_max_attempts", retry_max_attempts)
        object.__setattr__(self, "retry_backoff_seconds", retry_backoff_seconds)
        object.__setattr__(self, "retry_status_codes", retry_status_codes)
        object.__setattr__(self, "retry_methods", retry_methods)

    @property
    def base_url(self) -> str:
        """Return the API URL using the backward-compatible attribute name."""
        return self.url

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
            return cls(url="", api_token="")

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
        url = cfg.get("url") or cfg.get("base_url")
        if not url:
            msg = f"Section '{section}' in {expanded} must define 'url'."
            raise ValueError(msg)

        api_token = cfg.get("api_token")
        proxy = cfg.get("proxy")
        timeout = cfg.getfloat("timeout", fallback=30.0)

        return cls(
            url=url,
            api_token=api_token,
            proxy=proxy,
            timeout=timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        url_env: str = DEFAULT_URL_ENV,
        proxy_env: str = DEFAULT_PROXY_ENV,
        api_token_env: str = DEFAULT_API_TOKEN_ENV,
        base_url_env: str | None = None,
    ) -> OqtopusConfig:
        """Load configuration from environment variables.

        Args:
            url_env (Optional): Environment variable name used for the API URL.
                Defaults to ``OQTOPUS_URL``.
            proxy_env (Optional): Environment variable name used for the proxy
                URL. Defaults to ``OQTOPUS_PROXY``.
            api_token_env (Optional): Environment variable name used for the API
                token. Defaults to ``OQTOPUS_API_TOKEN``.
            base_url_env (Optional): Backward-compatible alias for ``url_env``.
                When omitted with the default ``url_env``, ``OQTOPUS_BASE_URL``
                is used as a fallback.

        Returns:
            Configuration loaded from environment variables.

        Raises:
            ValueError: If neither URL environment variable is set.

        """
        url_env_names: tuple[str, ...]
        if base_url_env is not None:
            url = os.getenv(base_url_env)
            url_env_names = (base_url_env,)
        else:
            url = os.getenv(url_env)
            url_env_names = (url_env,)
            if not url and url_env == DEFAULT_URL_ENV:
                url = os.getenv(DEFAULT_BASE_URL_ENV)
                url_env_names += (DEFAULT_BASE_URL_ENV,)
        if not url:
            names = " or ".join(url_env_names)
            msg = f"Environment variable {names} is required."
            raise ValueError(msg)

        api_token = os.getenv(api_token_env)
        return cls(
            url=url,
            api_token=api_token,
            proxy=os.getenv(proxy_env),
        )
