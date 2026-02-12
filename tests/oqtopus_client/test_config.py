from __future__ import annotations

from pathlib import Path

import pytest

from oqtopus_client.config import OqtopusConfig


def test_from_file_validates_section_and_path_not_none() -> None:
    with pytest.raises(ValueError):
        OqtopusConfig.from_file(section=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        OqtopusConfig.from_file(path=None)  # type: ignore[arg-type]


def test_from_file_raises_when_section_is_missing(tmp_path: Path) -> None:
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text("[default]\nbase_url=https://api.example.com\n", encoding="utf-8")
    with pytest.raises(ValueError):
        OqtopusConfig.from_file("missing", config_file)


def test_from_file_raises_when_base_url_and_url_are_missing(tmp_path: Path) -> None:
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text("[profile]\napi_token=t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        OqtopusConfig.from_file("profile", config_file)


def test_from_file_supports_url_fallback_and_token_file(tmp_path: Path) -> None:
    token_path = tmp_path / "token.txt"
    config_file = tmp_path / "oqtopus.ini"
    config_file.write_text(
        (
            "[profile]\n"
            "url=https://api.example.com\n"
            f"api_token_file={token_path}\n"
            "timeout=12.5\n"
        ),
        encoding="utf-8",
    )

    config = OqtopusConfig.from_file("profile", config_file)
    assert config.base_url == "https://api.example.com"
    assert config.api_token_file == token_path
    assert config.timeout == 12.5


def test_from_env_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OQTOPUS_BASE_URL", raising=False)
    with pytest.raises(ValueError):
        OqtopusConfig.from_env()


def test_from_env_reads_token_file_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    token_path = tmp_path / "token.json"
    monkeypatch.setenv("OQTOPUS_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("OQTOPUS_API_TOKEN", "secret")
    monkeypatch.setenv("OQTOPUS_API_TOKEN_FILE", str(token_path))

    config = OqtopusConfig.from_env()
    assert config.base_url == "https://api.example.com"
    assert config.api_token == "secret"
    assert config.api_token_file == token_path


def test_from_file_returns_empty_config_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    config = OqtopusConfig.from_file(section=None, path=None)  # type: ignore[arg-type]
    assert config.base_url == ""
    assert config.api_token == ""
