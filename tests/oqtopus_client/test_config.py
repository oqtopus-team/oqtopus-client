"""Unit tests for oqtopus-client."""

from __future__ import annotations

from pathlib import Path

import pytest

from oqtopus_client import OqtopusConfig


def test_from_file_validates_section_and_path_not_none() -> None:
    """Test case: test_from_file_validates_section_and_path_not_none."""
    with pytest.raises(ValueError):
        OqtopusConfig.from_file(section=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        OqtopusConfig.from_file(path=None)  # type: ignore[arg-type]


def test_from_file_raises_when_section_is_missing(tmp_path: Path) -> None:
    """Test case: test_from_file_raises_when_section_is_missing."""
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text("[default]\nbase_url=https://api.example.com\n", encoding="utf-8")
    with pytest.raises(ValueError):
        OqtopusConfig.from_file("missing", config_file)


def test_from_file_raises_when_base_url_and_url_are_missing(tmp_path: Path) -> None:
    """Test case: test_from_file_raises_when_base_url_is_missing."""
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text("[profile]\napi_token=t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        OqtopusConfig.from_file("profile", config_file)


def test_from_file_reads_base_url_and_token(tmp_path: Path) -> None:
    """Test case: test_from_file_reads_base_url_and_token."""
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text(
        (
            "[profile]\n"
            "base_url=https://api.example.com\n"
            "api_token=secret\n"
            "timeout=12.5\n"
        ),
        encoding="utf-8",
    )

    config = OqtopusConfig.from_file("profile", config_file)
    assert config.base_url == "https://api.example.com"
    assert config.api_token == "secret"
    assert config.timeout == 12.5


def test_from_file_reads_proxy(tmp_path: Path) -> None:
    """Test case: test_from_file_reads_proxy."""
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text(
        (
            "[profile]\n"
            "base_url=https://api.example.com\n"
            "api_token=t\n"
            "proxy=http://proxy.local:8080\n"
        ),
        encoding="utf-8",
    )
    config = OqtopusConfig.from_file("profile", config_file)
    assert config.proxy == "http://proxy.local:8080"


def test_from_file_uses_xdg_config_home_when_path_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_from_file_uses_xdg_config_home_when_path_is_omitted."""
    xdg_dir = tmp_path / "xdg"
    config_file = xdg_dir / "oqtopus" / "config.ini"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        "[default]\nbase_url=https://api.example.com\napi_token=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))

    config = OqtopusConfig.from_file()

    assert config.base_url == "https://api.example.com"
    assert config.api_token == "secret"


def test_from_file_falls_back_to_home_config_when_xdg_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_from_file_falls_back_to_home_config_when_xdg_is_unset."""
    config_file = tmp_path / ".config" / "oqtopus" / "config.ini"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        "[default]\nbase_url=https://api.example.com\napi_token=secret\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    config = OqtopusConfig.from_file()

    assert config.base_url == "https://api.example.com"
    assert config.api_token == "secret"


def test_from_env_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_from_env_requires_base_url."""
    monkeypatch.delenv("OQTOPUS_BASE_URL", raising=False)
    with pytest.raises(ValueError):
        OqtopusConfig.from_env()


def test_from_env_reads_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_from_env_reads_api_token."""
    monkeypatch.setenv("OQTOPUS_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("OQTOPUS_API_TOKEN", "secret")
    monkeypatch.setenv("OQTOPUS_PROXY", "http://proxy.local:8080")

    config = OqtopusConfig.from_env()
    assert config.base_url == "https://api.example.com"
    assert config.api_token == "secret"
    assert config.proxy == "http://proxy.local:8080"


def test_constructor_rejects_url_alias() -> None:
    """Test case: test_constructor_rejects_url_alias."""
    with pytest.raises(TypeError):
        OqtopusConfig(url="https://api.example.com", api_token="token")  # type: ignore[call-arg]


def test_repr_hides_api_token_and_proxy() -> None:
    """Test case: test_repr_hides_api_token_and_proxy."""
    config = OqtopusConfig(
        base_url="https://api.example.com",
        api_token="sk-live-EXAMPLE",
        proxy="http://user:pass@proxy.local:8080",
    )

    text = repr(config)

    assert "sk-live-EXAMPLE" not in text
    assert "user:pass@proxy.local" not in text
    assert "api_token" not in text
    assert "proxy" not in text
    assert "https://api.example.com" in text
    assert config.api_token == "sk-live-EXAMPLE"
    assert config.proxy == "http://user:pass@proxy.local:8080"


def test_from_file_returns_empty_config_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_from_file_returns_empty_config_in_sse_container."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    config = OqtopusConfig.from_file(section=None, path=None)  # type: ignore[arg-type]
    assert config.base_url == ""
    assert config.api_token == ""
