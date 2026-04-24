"""Unit tests for storage helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import aiohttp
import pytest

from oqtopus_client import rest as models
from oqtopus_client.services.storage import OqtopusStorage, OqtopusStorageError


def _presigned_url() -> models.JobsJobInfoUploadPresignedURL:
    return models.JobsJobInfoUploadPresignedURL(
        url="https://example.invalid/upload",
        fields=models.JobsJobInfoUploadPresignedURLFields(key="job-1/input.zip"),
    )


def test_download_file_url_roundtrip(tmp_path: Path) -> None:
    """Test case: test_download_file_url_roundtrip."""
    archive = tmp_path / "input.zip"
    archive.write_bytes(
        OqtopusStorage._build_zip_payload(
            {"program": ["OPENQASM 3;"]},
            "input.zip",
        )
    )

    payload = asyncio.run(OqtopusStorage.download(archive.resolve().as_uri()))

    assert payload == {"program": ["OPENQASM 3;"]}


def test_download_file_url_rejects_invalid_zip(tmp_path: Path) -> None:
    """Test case: test_download_file_url_rejects_invalid_zip."""
    archive = tmp_path / "broken.zip"
    archive.write_bytes(b"not-a-zip")

    with pytest.raises(OqtopusStorageError, match="Invalid ZIP file"):
        asyncio.run(OqtopusStorage.download(archive.resolve().as_uri()))


def test_download_http_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_download_http_roundtrip."""
    payload = OqtopusStorage._build_zip_payload(
        {"result": {"sampling": {"counts": {"00": 1}}}},
        "result.zip",
    )

    class _Response:
        def __init__(self, body: bytes) -> None:
            self._body = body

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def read(self) -> bytes:
            return self._body

    class _Session:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def get(self, url: str) -> _Response:
            assert url == "https://example.invalid/result.zip"
            return _Response(payload)

    monkeypatch.setattr("oqtopus_client.services.storage.aiohttp.ClientSession", _Session)

    downloaded = asyncio.run(
        OqtopusStorage.download("https://example.invalid/result.zip")
    )

    assert downloaded == {"result": {"sampling": {"counts": {"00": 1}}}}


def test_upload_posts_presigned_form(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_upload_posts_presigned_form."""
    observed: dict[str, object] = {}

    class _Response:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

    class _Session:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def post(self, url: str, *, data: object) -> _Response:
            observed["url"] = url
            observed["data"] = data
            return _Response()

    monkeypatch.setattr("oqtopus_client.services.storage.aiohttp.ClientSession", _Session)

    asyncio.run(
        OqtopusStorage.upload(
            _presigned_url(),
            {"program": ["OPENQASM 3;"]},
        )
    )

    assert observed["url"] == "https://example.invalid/upload"
    assert observed["data"].__class__.__name__ == "FormData"


def test_upload_wraps_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_upload_wraps_network_errors."""
    class _Session:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def post(self, url: str, *, data: object) -> object:
            _ = (url, data)
            msg = "boom"
            raise aiohttp.ClientError(msg)

    monkeypatch.setattr("oqtopus_client.services.storage.aiohttp.ClientSession", _Session)

    with pytest.raises(OqtopusStorageError, match="Network error during upload"):
        asyncio.run(
            OqtopusStorage.upload(
                _presigned_url(),
                {"program": ["OPENQASM 3;"]},
            )
        )
