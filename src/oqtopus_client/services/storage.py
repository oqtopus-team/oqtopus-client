"""Storage helpers for OQTOPUS presigned upload/download flows."""

from __future__ import annotations

import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import aiohttp

if TYPE_CHECKING:
    from oqtopus_client import rest as models


class OqtopusStorageError(Exception):
    """Raised when presigned upload/download operations fail."""


class OqtopusStorage:
    """Helpers for downloading and uploading job payloads via presigned URLs."""

    DEFAULT_TIMEOUT_S = 60

    @staticmethod
    def _build_zip_payload(data: dict[str, object], archive_name: str) -> bytes:
        with BytesIO() as zip_buffer:
            with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zip_arch:
                zip_arch.writestr(
                    f"{Path(archive_name).stem}.json",
                    json.dumps(data),
                )
            return zip_buffer.getvalue()

    @staticmethod
    def _extract_zip_object(
        zip_bytes: bytes,
        *,
        allow_non_dict: bool = False,
    ) -> dict[str, object] | str:
        try:
            with ZipFile(BytesIO(zip_bytes), "r") as zip_arch:
                json_file_path_list = zip_arch.namelist()
                if len(json_file_path_list) != 1:
                    msg = (
                        "Expected one file in single ZIP archive, "
                        f"but found {len(json_file_path_list)}."
                    )
                    raise OqtopusStorageError(msg)

                with zip_arch.open(json_file_path_list[0]) as json_file:
                    data = json.loads(json_file.read())
        except BadZipFile as exc:
            msg = "Invalid ZIP file"
            raise OqtopusStorageError(msg) from exc
        except json.JSONDecodeError as exc:
            msg = "Invalid JSON in ZIP file"
            raise OqtopusStorageError(msg) from exc

        if isinstance(data, dict):
            return data
        if allow_non_dict and isinstance(data, str):
            return data
        msg = f"Expected JSON root to be an object but got {type(data).__name__}."
        raise OqtopusStorageError(msg)

    @classmethod
    async def upload(
        cls,
        presigned_url: models.JobsJobInfoUploadPresignedURL,
        data: dict[str, object],
        *,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> None:
        """Upload one zipped JSON object using a presigned form POST.

        Raises:
            OqtopusStorageError: If the upload fails.

        """
        archive_name = Path(presigned_url.fields.key).name
        payload = cls._build_zip_payload(data, archive_name)
        form = aiohttp.FormData()
        for key, value in presigned_url.fields.to_dict().items():
            form.add_field(key, str(value))
        form.add_field(
            "file",
            payload,
            filename=archive_name,
            content_type="application/zip",
        )
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        try:
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.post(presigned_url.url, data=form) as response,
            ):
                response.raise_for_status()
        except aiohttp.ClientError as exc:
            msg = f"Network error during upload: {exc}"
            raise OqtopusStorageError(msg) from exc

    @classmethod
    async def download(
        cls,
        presigned_url: str,
        *,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        allow_non_dict: bool = False,
    ) -> dict[str, object] | str:
        """Download one zipped JSON object from a presigned URL.

        Returns:
            The extracted JSON payload as a dict or string.

        Raises:
            OqtopusStorageError: If the download fails.

        """
        parsed = urlparse(presigned_url)
        if parsed.scheme == "file":
            zip_bytes = await asyncio.to_thread(Path(parsed.path).read_bytes)
            return cls._extract_zip_object(
                zip_bytes,
                allow_non_dict=allow_non_dict,
            )

        timeout = aiohttp.ClientTimeout(total=timeout_s)
        try:
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.get(presigned_url) as response,
            ):
                response.raise_for_status()
                return cls._extract_zip_object(
                    await response.read(),
                    allow_non_dict=allow_non_dict,
                )
        except aiohttp.ClientError as exc:
            msg = f"Network error during download: {exc}"
            raise OqtopusStorageError(msg) from exc
