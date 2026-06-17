"""Core module for oqtopus-client."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, TypeVar, cast

from pydantic import TypeAdapter, ValidationError

from oqtopus_client import rest as models
from oqtopus_client.rest.api.announcements_api import AnnouncementsApi
from oqtopus_client.rest.api.api_token_api import ApiTokenApi
from oqtopus_client.rest.api.device_api import DeviceApi
from oqtopus_client.rest.api.job_api import JobApi
from oqtopus_client.rest.api_client import ApiClient as RestApiClient
from oqtopus_client.rest.configuration import Configuration as RestConfiguration
from oqtopus_client.rest.exceptions import ApiException as RestApiException
from oqtopus_client.rest.models.jobs_get_sselog_response import JobsGetSselogResponse
from oqtopus_client.rest.models.jobs_submit_job_info import JobsSubmitJobInfo
from oqtopus_client.services.config import OqtopusConfig
from oqtopus_client.services.device import (
    OqtopusDevice,
)
from oqtopus_client.services.errors import ResponseValidationError, UserApiError
from oqtopus_client.services.job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from oqtopus_client.services.job_spec import OqtopusJobSpec
from oqtopus_client.services.storage import OqtopusStorage

if TYPE_CHECKING:
    from datetime import datetime

PACKAGE_NAME = "oqtopus-client"
_SubmitJobInput = (
    models.JobsSubmitJobRequest | Mapping[str, object] | OqtopusJobSpec
)
_RunInput = _SubmitJobInput
_DEFAULT_BLOCKING_MAX_WORKERS = 4
_T = TypeVar("_T")


def _resolve_user_agent() -> str:
    try:
        package_version = version(PACKAGE_NAME)
    except PackageNotFoundError:
        package_version = "unknown"
    return f"{PACKAGE_NAME}/{package_version}"


class _AsyncOqtopusClient:  # noqa: PLR0904
    def __init__(
        self,
        config: OqtopusConfig,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        if not config.base_url and not self._is_sse_container():
            msg = "config.base_url is required."
            raise ValueError(msg)

        self.base_url = config.base_url.rstrip("/") if config.base_url else ""
        self._proxy = config.proxy
        self._headers: dict[str, str] = {
            "User-Agent": user_agent or _resolve_user_agent()
        }

        if config.retry_max_attempts < 1:
            msg = "retry_max_attempts must be >= 1."
            raise ValueError(msg)
        if config.retry_backoff_seconds < 0:
            msg = "retry_backoff_seconds must be >= 0."
            raise ValueError(msg)
        self._retry_max_attempts = config.retry_max_attempts
        self._retry_backoff_seconds = config.retry_backoff_seconds
        self._retry_status_codes = set(config.retry_status_codes or {429})
        self._retry_methods = {
            m.upper() for m in (config.retry_methods or {"GET", "DELETE"})
        }
        self._rest_timeout = config.timeout

        if default_headers:
            self._headers.update(default_headers)

        self._rest_config: RestConfiguration
        self._rest_client: RestApiClient
        self._job_api: JobApi
        self._device_api: DeviceApi
        self._token_api: ApiTokenApi
        self._announcements_api: AnnouncementsApi

        token = config.api_token
        if token:
            self._apply_api_token(token)
        self._initialize_rest_api()

    def _apply_api_token(self, api_token: str) -> None:
        self._headers["q-api-token"] = api_token

    def _initialize_rest_api(self) -> None:  # pragma: no cover - integration path
        self._rest_config = RestConfiguration(host=self.base_url)
        self._rest_config.proxy = self._proxy
        self._rest_config.retries = (
            self._retry_max_attempts if self._retry_max_attempts > 1 else None
        )
        self._rest_client = RestApiClient(
            configuration=self._rest_config
        )
        self._rest_client.user_agent = self._headers["User-Agent"]
        for header_name, header_value in self._headers.items():
            self._rest_client.set_default_header(header_name, header_value)
        self._job_api = JobApi(self._rest_client)
        self._device_api = DeviceApi(self._rest_client)
        self._token_api = ApiTokenApi(self._rest_client)
        self._announcements_api = AnnouncementsApi(self._rest_client)

    async def close(self) -> None:
        await self._rest_client.close()  # pragma: no cover - integration path

    async def _call_rest(
        self, call: Awaitable[_T]
    ) -> _T:  # pragma: no cover - integration path
        try:
            return await call
        except RestApiException as exc:
            payload = exc.data if exc.data is not None else exc.body
            message = (
                self._extract_error_message(payload) or exc.reason or "request failed"
            )
            raise UserApiError(exc.status or 0, message, payload=payload) from exc

    @staticmethod
    def _job_type_of(
        job: models.JobsSubmitJobRequest | Mapping[str, object] | OqtopusJobSpec,
    ) -> str | None:
        if isinstance(job, OqtopusJobSpec):
            spec_job_type = job.job_type
            return (
                spec_job_type.value
                if isinstance(spec_job_type, models.JobsJobType)
                else spec_job_type
                if isinstance(spec_job_type, str)
                else None
            )
        if isinstance(job, models.JobsSubmitJobRequest):
            return job.job_type.value
        mapping_job_type = job.get("job_type")
        return (
            mapping_job_type.value
            if isinstance(mapping_job_type, models.JobsJobType)
            else mapping_job_type
            if isinstance(mapping_job_type, str)
            else None
        )

    @staticmethod
    def _to_submit_job_request(
        job: _RunInput,
    ) -> models.JobsSubmitJobRequest:
        if isinstance(job, models.JobsSubmitJobRequest):
            return job
        if isinstance(job, OqtopusJobSpec):
            return job.to_model()
        payload = dict(job)
        payload.pop("job_info", None)
        return models.JobsSubmitJobRequest.model_validate(payload)

    @staticmethod
    def _extract_legacy_job_info_payload(job: _RunInput) -> object | None:
        if isinstance(job, Mapping):
            return job.get("job_info")
        return getattr(job, "job_info", None)

    @classmethod
    def _to_s3_submit_job_info(
        cls,
        job: _RunInput,
    ) -> models.JobsS3SubmitJobInfo:
        if isinstance(job, OqtopusJobSpec):
            return job.to_s3_submit_job_info()

        job_info = cls._extract_legacy_job_info_payload(job)
        if isinstance(job_info, models.JobsS3SubmitJobInfo):
            return job_info
        if isinstance(job_info, JobsSubmitJobInfo):
            return models.JobsS3SubmitJobInfo(
                program=job_info.program,
                operator=(
                    [
                        models.JobsS3OperatorItem(
                            pauli=item.pauli,
                            coeff=item.coeff,
                        )
                        for item in job_info.operator
                    ]
                    if job_info.operator is not None
                    else None
                ),
            )
        if isinstance(job_info, Mapping):
            s3_job_info = models.JobsS3SubmitJobInfo.from_dict(dict(job_info))
            if s3_job_info is not None:
                return s3_job_info

        msg = (
            "job payload must include program data for S3 offload. "
            "Use OqtopusJobSpec or provide a legacy job_info mapping."
        )
        raise ValueError(msg)

    @staticmethod
    def _looks_like_presigned_url(value: object) -> bool:
        return isinstance(value, str) and value.startswith(
            ("http://", "https://", "file://")
        )

    @classmethod
    def _validate_run_job_type(
        cls,
        job: models.JobsSubmitJobRequest | Mapping[str, object] | OqtopusJobSpec,
        expected: models.JobsJobType,
    ) -> None:
        actual = cls._job_type_of(job)
        if actual != expected.value:
            msg = (
                f"job_type must be '{expected.value}' for this helper "
                f"(got {actual!r})."
            )
            raise ValueError(msg)

    @staticmethod
    def _extract_error_message(payload: object) -> str | None:
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message
            error = payload.get("error")
            if isinstance(error, str) and error.strip():
                return error
            if isinstance(error, dict):
                detail = error.get("message")
                if isinstance(detail, str) and detail.strip():
                    return detail
        if isinstance(payload, str):
            text = payload.strip()
            return text or None
        return None

    @staticmethod
    def _is_sse_container() -> bool:
        return os.getenv("OQTOPUS_ENV") == "sse_container"

    @classmethod
    async def _run_sse_container_job(
        cls,
        request: models.JobsSubmitJobRequest,
        upload_info: models.JobsS3SubmitJobInfo,
    ) -> models.JobsJob:
        try:
            sse_driver = import_module("sse_driver")
        except ModuleNotFoundError as exc:
            raise UserApiError(
                0,
                "sse_container mode requires 'sse_driver' module.",
                payload={"mode": "sse_container"},
            ) from exc

        try:
            response = await asyncio.to_thread(
                    sse_driver.submit_job,
                    request,
                    upload_info
            )
        except Exception as exc:  # pragma: no cover - surfaced as API error
            raise UserApiError(
                0,
                f"sse_container execution failed: {exc}",
                payload={"mode": "sse_container", "job_type": request.job_type.value},
            ) from exc

        response_payload: object = response
        # Accept pydantic model instances returned by external runtime modules,
        # including models generated from a different package version.
        if hasattr(response, "model_dump_json") and callable(
            response.model_dump_json
        ):  # pragma: no cover
            response_payload = json.loads(response.model_dump_json())
        elif hasattr(response, "json") and callable(response.json):  # pragma: no cover
            response_payload = json.loads(response.json())
        elif hasattr(response, "model_dump") and callable(
            response.model_dump
        ):  # pragma: no cover
            response_payload = response.model_dump(mode="json")
        elif hasattr(response, "dict") and callable(response.dict):  # pragma: no cover
            response_payload = response.dict()

        response_payload = cls._normalize_sse_container_response(response_payload)

        try:
            return TypeAdapter(models.JobsJob).validate_python(response_payload)
        except ValidationError as exc:
            try:
                return models.JobsJob.model_validate(response, from_attributes=True)
            except ValidationError:  # pragma: no cover
                raise ResponseValidationError(str(exc), response_payload) from exc

    @staticmethod
    def _normalize_sse_container_response(response_payload: object) -> object:
        if not isinstance(response_payload, dict):
            return response_payload
        if "job_info" in response_payload:
            return response_payload

        job_info_keys = (
            "input",
            "combined_program",
            "result",
            "transpile_result",
            "sse_log",
            "message",
        )
        if not any(key in response_payload for key in job_info_keys):
            return response_payload

        normalized = dict(response_payload)
        normalized["job_info"] = {
            key: normalized.pop(key)
            for key in job_info_keys
            if key in normalized
        }
        return normalized

    @classmethod
    async def _resolve_job_info_item(
        cls,
        value: object | None,
        *,
        parser: Callable[[dict[str, object]], object] | None = None,
        allow_non_dict: bool = False,
        proxy: str | None = None,
    ) -> object | None:
        if value is None or not cls._looks_like_presigned_url(value):
            return value
        downloaded = await OqtopusStorage.download(
            str(value),
            allow_non_dict=allow_non_dict,
            proxy=proxy,
        )
        if parser is not None and isinstance(downloaded, dict):
            return parser(downloaded)
        return downloaded

    @classmethod
    async def _resolve_job_info(
        cls,
        job_info: models.JobsJobInfo | None,
        *,
        proxy: str | None = None,
    ) -> models.JobsJobInfo | None:
        if job_info is None:
            return None

        resolved = {
            "input": await cls._resolve_job_info_item(
                job_info.input,
                parser=models.JobsS3SubmitJobInfo.from_dict,
                proxy=proxy,
            ),
            "combined_program": await cls._resolve_job_info_item(
                job_info.combined_program,
                allow_non_dict=True,
                proxy=proxy,
            ),
            "result": await cls._resolve_job_info_item(
                job_info.result,
                parser=models.JobsS3JobResult.from_dict,
                proxy=proxy,
            ),
            "transpile_result": await cls._resolve_job_info_item(
                job_info.transpile_result,
                parser=models.JobsS3TranspileResult.from_dict,
                proxy=proxy,
            ),
            "sse_log": job_info.sse_log,
            "message": job_info.message,
        }
        return models.JobsJobInfo.from_dict(resolved)

    async def _resolve_job(self, job: models.JobsJob) -> models.JobsJob:
        if job.status == models.JobsJobStatus.REGISTERED:
            msg = "registered job (status='registered') is not supported here"
            raise ResponseValidationError(msg, job.model_dump(mode="json"))
        return job.model_copy(
            update={
                "job_info": await self._resolve_job_info(
                    job.job_info,
                    proxy=self._proxy,
                )
            }
        )

    async def list_devices(self) -> list[models.DevicesDeviceInfo]:
        device_api = self._device_api
        return cast(
            "list[models.DevicesDeviceInfo]",
            await self._call_rest(
                device_api.list_devices(_request_timeout=self._rest_timeout)
            ),
        )

    async def get_device(self, device_id: str) -> models.DevicesDeviceInfo:
        device_api = self._device_api
        return cast(
            "models.DevicesDeviceInfo",
            await self._call_rest(
                device_api.get_device(
                    device_id,
                    _request_timeout=self._rest_timeout,
                )
            ),
        )

    async def list_jobs(  # noqa: PLR0913
        self,
        *,
        fields: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: models.JobsJobStatus | None = None,
        q: str | None = None,
        page: int | None = None,
        size: int | None = None,
        order: str | None = None,
    ) -> list[models.JobsJob]:
        job_api = self._job_api
        return cast(
            "list[models.JobsJob]",
            await self._call_rest(
                job_api.list_jobs(
                    fields=fields,
                    start_time=start_time,
                    end_time=end_time,
                    status=status,
                    q=q,
                    page=page,
                    size=size,
                    order=order,
                    _request_timeout=self._rest_timeout,
                ),
            ),
        )

    async def submit_job(
        self,
        body: _SubmitJobInput,
    ) -> models.JobsRegisterJobResponse:
        job_api = self._job_api
        request = self._to_submit_job_request(body)
        upload_info = self._to_s3_submit_job_info(body)
        register_response = cast(
            "models.JobsRegisterJobResponse",
            await self._call_rest(
                job_api.register_job_id(_request_timeout=self._rest_timeout)
            ),
        )
        await OqtopusStorage.upload(
            register_response.presigned_url,
            upload_info.to_dict(),
            timeout_s=int(self._rest_timeout or OqtopusStorage.DEFAULT_TIMEOUT_S),
            proxy=self._proxy,
        )
        await self._call_rest(
            job_api.submit_job(
                register_response.job_id,
                request,
                _request_timeout=self._rest_timeout,
            )
        )
        return register_response

    async def run_job(  # noqa: PLR0913
        self,
        job: _SubmitJobInput,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        request = self._to_submit_job_request(job)
        upload_info = self._to_s3_submit_job_info(job)
        if self._is_sse_container():
            if request.job_type in {
                models.JobsJobType.SAMPLING,
                models.JobsJobType.MULTI_MANUAL,
                models.JobsJobType.ESTIMATION,
                models.JobsJobType.SSE,
            }:
                return await self._run_sse_container_job(request, upload_info)
            raise UserApiError(  # pragma: no cover - defensive branch
                0,
                (
                    f"job_type '{request.job_type.value}' is not supported in "
                    "sse_container mode."
                ),
                payload={"mode": "sse_container", "job_type": request.job_type.value},
            )

        response = await self.submit_job(job)
        return await self.wait_for_job(
            response.job_id,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def _run_job_with_type(  # noqa: PLR0913
        self,
        job: _RunInput,
        *,
        expected: models.JobsJobType,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        request = self._to_submit_job_request(job)
        self._validate_run_job_type(request, expected)
        return await self.run_job(
            job,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def run_sampling(  # noqa: PLR0913
        self,
        job: _RunInput,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        return await self._run_job_with_type(
            job,
            expected=models.JobsJobType.SAMPLING,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def run_estimation(  # noqa: PLR0913
        self,
        job: _RunInput,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        return await self._run_job_with_type(
            job,
            expected=models.JobsJobType.ESTIMATION,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def run_multi_manual(  # noqa: PLR0913
        self,
        job: _RunInput,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        return await self._run_job_with_type(
            job,
            expected=models.JobsJobType.MULTI_MANUAL,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def run_sse(  # noqa: PLR0913
        self,
        job: _RunInput,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        return await self._run_job_with_type(
            job,
            expected=models.JobsJobType.SSE,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    @staticmethod
    def build_sse_job_request(  # noqa: PLR0913
        file_path: str | Path,
        *,
        device_id: str,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict[str, object] | None = None,
        simulator_info: dict[str, object] | None = None,
        mitigation_info: dict[str, object] | None = None,
        shots: int = 1,
        max_file_size: int = 10 * 1024 * 1024,
    ) -> OqtopusJobSpec:
        path = Path(file_path)
        if not path.exists():
            msg = f"The file does not exist: {path}"
            raise ValueError(msg)
        if not path.is_file():
            msg = f"The path is not a file: {path}"
            raise ValueError(msg)
        if path.suffix != ".py":
            msg = f"The file is not python file: {path}"
            raise ValueError(msg)

        raw_bytes = path.read_bytes()
        if len(raw_bytes) >= max_file_size:
            msg = f"size of the file is larger than {max_file_size}"
            raise ValueError(msg)

        try:
            program = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            msg = f"SSE user program must be UTF-8 text: {path}"
            raise ValueError(msg) from exc

        return OqtopusJobSpec.sse(
            name=name,
            description=description,
            device_id=device_id,
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            shots=shots,
            program=program,
        )

    async def run_sse_file(  # noqa: PLR0913
        self,
        *,
        file_path: str | Path,
        device_id: str,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict[str, object] | None = None,
        simulator_info: dict[str, object] | None = None,
        mitigation_info: dict[str, object] | None = None,
        shots: int = 1,
        max_file_size: int = 10 * 1024 * 1024,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        request = self.build_sse_job_request(
            file_path=file_path,
            device_id=device_id,
            name=name,
            description=description,
            transpiler_info=transpiler_info,
            simulator_info=simulator_info,
            mitigation_info=mitigation_info,
            shots=shots,
            max_file_size=max_file_size,
        )
        return await self.run_sse(
            request,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    async def get_job(self, job_id: str) -> models.JobsJob:
        job_api = self._job_api
        job = cast(
            "models.JobsJob",
            await self._call_rest(
                job_api.get_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )
        return await self._resolve_job(job)

    @staticmethod
    def _validate_wait_for_job_args(
        *,
        interval: float,
        interval_backoff: float,
        max_interval: float | None,
        timeout: float | None,
    ) -> None:
        if interval <= 0:
            msg = "interval must be greater than 0."
            raise ValueError(msg)
        if interval_backoff < 1.0:
            msg = "interval_backoff must be >= 1.0."
            raise ValueError(msg)
        if max_interval is not None and max_interval <= 0:
            msg = "max_interval must be greater than 0 or None."
            raise ValueError(msg)
        if timeout is not None and timeout <= 0:
            msg = "timeout must be greater than 0 or None."
            raise ValueError(msg)

    @staticmethod
    def _resolve_terminal_statuses(
        terminal_statuses: set[models.JobsJobStatus] | None,
    ) -> set[models.JobsJobStatus]:
        return terminal_statuses or {
            models.JobsJobStatus.SUCCEEDED,
            models.JobsJobStatus.FAILED,
            models.JobsJobStatus.CANCELLED,
        }

    @staticmethod
    def _raise_wait_timeout(
        *,
        job_id: str,
        timeout: float | None,
        deadline: float | None,
    ) -> None:
        if deadline is None:
            return
        if monotonic() < deadline:
            return
        msg = f"Timed out waiting for job {job_id} after {timeout} seconds."
        raise TimeoutError(msg)

    @classmethod
    def _compute_wait_sleep_duration(
        cls,
        *,
        next_interval: float,
        deadline: float | None,
        job_id: str,
        timeout: float | None,
    ) -> float:
        if deadline is None:
            return next_interval

        remaining = deadline - monotonic()
        if remaining <= 0:
            cls._raise_wait_timeout(
                job_id=job_id,
                timeout=timeout,
                deadline=deadline,
            )
        return min(next_interval, remaining)

    @staticmethod
    def _next_wait_interval(
        *,
        current_interval: float,
        interval_backoff: float,
        max_interval: float | None,
    ) -> float:
        next_interval = current_interval * interval_backoff
        if max_interval is not None:
            return min(next_interval, max_interval)
        return next_interval

    async def wait_for_job(  # noqa: PLR0913
        self,
        job_id: str,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> models.JobsJob:
        self._validate_wait_for_job_args(
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
        )
        terminal = self._resolve_terminal_statuses(terminal_statuses)
        _ = failure_statuses

        deadline = monotonic() + timeout if timeout is not None else None
        next_interval = interval

        while True:
            status_response = await self.get_job_status(job_id)
            if on_status is not None:
                on_status(status_response)
            current = status_response.status
            if current in terminal:
                return await self.get_job(job_id)

            self._raise_wait_timeout(
                job_id=job_id,
                timeout=timeout,
                deadline=deadline,
            )
            sleep_for = self._compute_wait_sleep_duration(
                next_interval=next_interval,
                deadline=deadline,
                job_id=job_id,
                timeout=timeout,
            )

            await asyncio.sleep(sleep_for)
            next_interval = self._next_wait_interval(
                current_interval=next_interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
            )

    async def delete_job(self, job_id: str) -> models.SuccessSuccessResponse:
        job_api = self._job_api
        return cast(
            "models.SuccessSuccessResponse",
            await self._call_rest(
                job_api.delete_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def get_job_status(self, job_id: str) -> models.JobsGetJobStatusResponse:
        job_api = self._job_api
        return cast(
            "models.JobsGetJobStatusResponse",
            await self._call_rest(
                job_api.get_job_status(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def cancel_job(self, job_id: str) -> models.SuccessSuccessResponse:
        job_api = self._job_api
        return cast(
            "models.SuccessSuccessResponse",
            await self._call_rest(
                job_api.cancel_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
        job = await self.get_job(job_id)
        sse_log = job.job_info.sse_log if job.job_info is not None else None
        if not isinstance(sse_log, str):
            msg = f"SSE log is not available for job {job_id}."
            raise ResponseValidationError(msg, job.model_dump(mode="json"))
        payload = await OqtopusStorage.download_archive(
            sse_log,
            timeout_s=int(self._rest_timeout or OqtopusStorage.DEFAULT_TIMEOUT_S),
            proxy=self._proxy,
        )
        return JobsGetSselogResponse(
            file=base64.b64encode(payload).decode("utf-8"),
            file_name=f"sselog_{job_id}.log",
        )

    async def create_api_token(self) -> models.ApiTokenApiToken:
        token_api = self._token_api
        token = cast(
            "models.ApiTokenApiToken",
            await self._call_rest(
                token_api.create_api_token(_request_timeout=self._rest_timeout)
            ),
        )
        if token is None:  # pragma: no cover
            msg = "create_api_token response is empty."
            raise ResponseValidationError(msg, token)
        return token

    async def get_api_token_status(self) -> models.ApiTokenApiTokenStatus:
        token_api = self._token_api
        return cast(
            "models.ApiTokenApiTokenStatus",
            await self._call_rest(
                token_api.get_api_token_status(_request_timeout=self._rest_timeout)
            ),
        )

    async def get_api_token(self) -> models.ApiTokenApiTokenStatus:
        return await self.get_api_token_status()

    async def delete_api_token(self) -> None:
        token_api = self._token_api
        await self._call_rest(
            token_api.delete_api_token(_request_timeout=self._rest_timeout)
        )

    async def get_announcements_list(
        self,
    ) -> models.AnnouncementsGetAnnouncementsListResponse:
        announcements_api = self._announcements_api
        return cast(
            "models.AnnouncementsGetAnnouncementsListResponse",
            await self._call_rest(
                announcements_api.get_announcements_list(
                    _request_timeout=self._rest_timeout
                )
            ),
        )

    async def get_announcement(
        self, announcement_id: int
    ) -> models.AnnouncementsGetAnnouncementResponse:
        announcements_api = self._announcements_api
        return cast(
            "models.AnnouncementsGetAnnouncementResponse",
            await self._call_rest(
                announcements_api.get_announcement(
                    announcement_id, _request_timeout=self._rest_timeout
                )
            ),
        )


class OqtopusClient:  # noqa: PLR0904
    """Synchronous public client; internal HTTP calls are executed asynchronously."""

    def __init__(
        self,
        config: OqtopusConfig | None = None,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Initialize the synchronous OQTOPUS client.

        Args:
            config (Optional): Client configuration bundle. If omitted,
                `OqtopusConfig.from_file()` is used. In normal mode, the resolved
                config must provide a non-empty `base_url`.
            default_headers (Optional): Additional headers merged into every
                request.
            user_agent (Optional): Custom User-Agent header value.

        """
        resolved_config = config or OqtopusConfig.from_file()
        self._config = resolved_config
        self._default_headers = dict(default_headers) if default_headers else None
        self._user_agent = user_agent
        self.base_url = (
            resolved_config.base_url.rstrip("/") if resolved_config.base_url else ""
        )
        self.timeout = resolved_config.timeout
        self.retry_max_attempts = resolved_config.retry_max_attempts
        self.retry_backoff_seconds = resolved_config.retry_backoff_seconds
        self.retry_status_codes = frozenset(resolved_config.retry_status_codes or {429})
        self.retry_methods = frozenset(
            m.upper() for m in (resolved_config.retry_methods or {"GET", "DELETE"})
        )

    def _run(
        self,
        coro_factory: Callable[[_AsyncOqtopusClient], Coroutine[object, object, _T]],
    ) -> _T:
        async def _main() -> _T:
            async_client = _AsyncOqtopusClient(
                self._config,
                self._default_headers,
                self._user_agent,
            )
            try:
                return await coro_factory(async_client)
            finally:
                with suppress(Exception):
                    await async_client.close()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_main())

        def _run_in_thread() -> _T:
            return asyncio.run(_main())

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_run_in_thread).result()

    async def _run_async_with_client(
        self,
        coro_factory: Callable[[_AsyncOqtopusClient], Coroutine[object, object, _T]],
    ) -> _T:
        async_client = _AsyncOqtopusClient(
            self._config,
            self._default_headers,
            self._user_agent,
        )
        try:
            return await coro_factory(async_client)
        finally:
            with suppress(Exception):
                await async_client.close()

    def _run_async_method(
        self,
        method: Callable[..., Coroutine[object, object, _T]],
        *args: object,
        **kwargs: object,
    ) -> _T:
        async def _invoke(async_client: _AsyncOqtopusClient) -> _T:
            bound_method = method.__get__(async_client, type(async_client))
            return await bound_method(*args, **kwargs)

        return self._run(_invoke)

    def _to_result(self, job: models.JobsJob) -> OqtopusJobResult:
        if job.job_type == models.JobsJobType.MULTI_MANUAL:
            return OqtopusMultiManualJobResult.from_raw(job, client=self)
        if job.job_type == models.JobsJobType.SSE:
            return OqtopusSseJobResult.from_raw(job, client=self)
        if job.job_type == models.JobsJobType.SAMPLING:
            return OqtopusSamplingJobResult.from_raw(job, client=self)
        if job.job_type == models.JobsJobType.ESTIMATION:
            return OqtopusEstimationJobResult.from_raw(job, client=self)
        return OqtopusJobResult.from_raw(job, client=self)  # pragma: no cover

    @staticmethod
    def _to_device(device: models.DevicesDeviceInfo) -> OqtopusDevice:
        return OqtopusDevice(raw=device)

    def _run_job_request(  # noqa: PLR0913
        self,
        job: _RunInput,
        runner: Callable[..., Coroutine[object, object, models.JobsJob]],
        *,
        interval: float,
        interval_backoff: float,
        max_interval: float | None,
        timeout: float | None,
        terminal_statuses: set[models.JobsJobStatus] | None,
        failure_statuses: set[models.JobsJobStatus] | None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None,
    ) -> models.JobsJob:
        return self._run_async_method(
            runner,
            job,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    def _run_typed_job(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        method_name: str,
        runner: Callable[..., Coroutine[object, object, models.JobsJob]],
        expected: models.JobsJobType | None = None,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusJobResult:
        spec = self._validate_job_spec(job, expected=expected, method=method_name)
        finished_job = self._run_job_request(
            spec,
            runner,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )
        return self._to_result(finished_job)

    @staticmethod
    def _coerce_typed_job_result(
        result: OqtopusJobResult,
        *,
        expected_type: type[_T],
        error_message: str,
    ) -> _T:
        if not isinstance(result, expected_type):
            raise ResponseValidationError(
                error_message,
                {
                    "job_id": result.job_id,
                    "job_type": (
                        result.job_type.value
                        if isinstance(result.job_type, models.JobsJobType)
                        else result.job_type
                    ),
                    "result_type": type(result).__name__,
                },
            )  # pragma: no cover
        return result

    def list_devices(self) -> list[OqtopusDevice]:
        """List available devices.

        Returns:
            Available devices wrapped as SDK device objects.

        """
        devices = self._run_async_method(_AsyncOqtopusClient.list_devices)
        return [self._to_device(device) for device in devices]

    def get_device(self, device_id: str) -> OqtopusDevice:
        """Get one device by id.

        Args:
            device_id (Required): Target device ID to fetch.

        Returns:
            The requested device wrapped as an SDK device object.

        """
        device = self._run_async_method(_AsyncOqtopusClient.get_device, device_id)
        return self._to_device(device)

    def list_jobs(  # noqa: PLR0913
        self,
        *,
        fields: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: models.JobsJobStatus | None = None,
        q: str | None = None,
        page: int | None = None,
        size: int | None = None,
        order: str | None = None,
    ) -> list[models.JobsJob]:
        """List jobs with optional filters.

        Returns:
            Jobs returned by the API.

        """
        return self._run_async_method(
            _AsyncOqtopusClient.list_jobs,
            fields=fields,
            start_time=start_time,
            end_time=end_time,
            status=status,
            q=q,
            page=page,
            size=size,
            order=order,
        )

    def submit_job(self, body: OqtopusJobSpec) -> models.JobsRegisterJobResponse:
        """Submit one job and return submission response.

        Args:
            body (Required): `OqtopusJobSpec`.

        Returns:
            Submission response for the created job.

        Raises:
            TypeError: If ``body`` is not an ``OqtopusJobSpec``.

        """
        if not isinstance(body, OqtopusJobSpec):
            msg = "submit_job expects OqtopusJobSpec."
            raise TypeError(msg)  # pragma: no cover
        return self._run_async_method(_AsyncOqtopusClient.submit_job, body)

    def submit_jobs(
        self,
        jobs: Sequence[OqtopusJobSpec],
        *,
        max_workers: int = 4,
    ) -> list[models.JobsRegisterJobResponse]:
        """Submit multiple jobs in parallel.

        Args:
            jobs (Required): List of `OqtopusJobSpec`.
            max_workers (Optional): Submission concurrency. Default is ``4``.

        Returns:
            Submission responses for all jobs.

        Raises:
            TypeError: If any item in ``jobs`` is not an ``OqtopusJobSpec``.
            ValueError: If ``max_workers`` is less than ``1``.

        """
        if max_workers < 1:
            msg = "max_workers must be >= 1."
            raise ValueError(msg)
        if any(not isinstance(job, OqtopusJobSpec) for job in jobs):
            msg = "submit_jobs expects a list of OqtopusJobSpec."
            raise TypeError(msg)  # pragma: no cover
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(self.submit_job, jobs))

    async def submit_jobs_async(
        self,
        jobs: Sequence[OqtopusJobSpec],
        *,
        max_workers: int = 4,
    ) -> list[models.JobsRegisterJobResponse]:
        """Submit multiple jobs concurrently in an async context.

        Args:
            jobs (Required): List of `OqtopusJobSpec`.
            max_workers (Optional): Submission concurrency. Default is ``4``.

        Returns:
            Submission responses for all jobs.

        Raises:
            TypeError: If any item in ``jobs`` is not an ``OqtopusJobSpec``.
            ValueError: If ``max_workers`` is less than ``1``.

        """
        if max_workers < 1:
            msg = "max_workers must be >= 1."
            raise ValueError(msg)
        if any(not isinstance(job, OqtopusJobSpec) for job in jobs):
            msg = "submit_jobs_async expects a list of OqtopusJobSpec."
            raise TypeError(msg)

        semaphore = asyncio.Semaphore(max_workers)

        async def _submit(job: OqtopusJobSpec) -> models.JobsRegisterJobResponse:
            async with semaphore:
                return await self._run_async_with_client(
                    lambda async_client: async_client.submit_job(job)
                )

        return await asyncio.gather(*(_submit(job) for job in jobs))

    @staticmethod
    def _validate_job_spec(
        job: OqtopusJobSpec,
        *,
        expected: models.JobsJobType | None = None,
        method: str = "run_job",
    ) -> OqtopusJobSpec:
        if not isinstance(job, OqtopusJobSpec):
            msg = f"{method} expects OqtopusJobSpec."
            raise TypeError(msg)  # pragma: no cover
        if expected is not None and models.JobsJobType(job.job_type) != expected:
            msg = (
                f"job.job_type must be '{expected.value}' for {method} "
                f"(got {job.job_type!r})."
            )
            raise ValueError(msg)
        return job

    def run_job(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusJobResult:
        """Submit one job spec, wait until completion, and return typed result.

        Args:
            job (Required): `OqtopusJobSpec`.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an SDK result wrapper.

        """
        return self._run_typed_job(
            job,
            method_name="run_job",
            runner=_AsyncOqtopusClient.run_job,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    def run_sampling(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusSamplingJobResult:
        """Run a sampling job and return sampling-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='sampling'``.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as a sampling result wrapper.

        """
        return self._coerce_typed_job_result(
            self._run_typed_job(
                job,
                method_name="run_sampling",
                runner=_AsyncOqtopusClient.run_sampling,
                expected=models.JobsJobType.SAMPLING,
                interval=interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
                timeout=timeout,
                terminal_statuses=terminal_statuses,
                failure_statuses=failure_statuses,
                on_status=on_status,
            ),
            expected_type=OqtopusSamplingJobResult,
            error_message="run_sampling returned non-sampling job result",
        )

    def run_estimation(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusEstimationJobResult:
        """Run an estimation job and return estimation-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='estimation'``.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an estimation result wrapper.

        """
        return self._coerce_typed_job_result(
            self._run_typed_job(
                job,
                method_name="run_estimation",
                runner=_AsyncOqtopusClient.run_estimation,
                expected=models.JobsJobType.ESTIMATION,
                interval=interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
                timeout=timeout,
                terminal_statuses=terminal_statuses,
                failure_statuses=failure_statuses,
                on_status=on_status,
            ),
            expected_type=OqtopusEstimationJobResult,
            error_message="run_estimation returned non-estimation job result",
        )

    def run_multi_manual(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusMultiManualJobResult:
        """Run a multi-manual job and return multi-manual-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='multi_manual'``.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as a multi-manual result wrapper.

        """
        return self._coerce_typed_job_result(
            self._run_typed_job(
                job,
                method_name="run_multi_manual",
                runner=_AsyncOqtopusClient.run_multi_manual,
                expected=models.JobsJobType.MULTI_MANUAL,
                interval=interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
                timeout=timeout,
                terminal_statuses=terminal_statuses,
                failure_statuses=failure_statuses,
                on_status=on_status,
            ),
            expected_type=OqtopusMultiManualJobResult,
            error_message="run_multi_manual returned non-multi_manual job result",
        )

    def run_sse(  # noqa: PLR0913
        self,
        job: OqtopusJobSpec,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusSseJobResult:
        """Run an SSE job and return SSE-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='sse'``.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an SSE result wrapper.

        """
        return self._coerce_typed_job_result(
            self._run_typed_job(
                job,
                method_name="run_sse",
                runner=_AsyncOqtopusClient.run_sse,
                expected=models.JobsJobType.SSE,
                interval=interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
                timeout=timeout,
                terminal_statuses=terminal_statuses,
                failure_statuses=failure_statuses,
                on_status=on_status,
            ),
            expected_type=OqtopusSseJobResult,
            error_message="run_sse returned non-sse job result",
        )

    def run_sse_file(  # noqa: PLR0913
        self,
        *,
        file_path: str | Path,
        device_id: str,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict[str, object] | None = None,
        simulator_info: dict[str, object] | None = None,
        mitigation_info: dict[str, object] | None = None,
        shots: int = 1,
        max_file_size: int = 10 * 1024 * 1024,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusSseJobResult:
        """Build and run an SSE job directly from a script file and return SSE result.

        Args:
            file_path (Required): Path to the Python script.
            device_id (Required): Target device ID.
            name (Optional): Job name.
            description (Optional): Job description.
            transpiler_info (Optional): Transpiler settings.
            simulator_info (Optional): Simulator settings.
            mitigation_info (Optional): Error mitigation settings.
            shots (Optional): Number of shots.
            max_file_size (Optional): Max script size in bytes.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an SSE result wrapper.

        """
        result = self._to_result(
            self._run_async_method(
                _AsyncOqtopusClient.run_sse_file,
                file_path=file_path,
                device_id=device_id,
                name=name,
                description=description,
                transpiler_info=transpiler_info,
                simulator_info=simulator_info,
                mitigation_info=mitigation_info,
                shots=shots,
                max_file_size=max_file_size,
                interval=interval,
                interval_backoff=interval_backoff,
                max_interval=max_interval,
                timeout=timeout,
                terminal_statuses=terminal_statuses,
                failure_statuses=failure_statuses,
                on_status=on_status,
            )
        )
        return self._coerce_typed_job_result(
            result,
            expected_type=OqtopusSseJobResult,
            error_message="run_sse_file returned non-sse job result",
        )

    def get_job(self, job_id: str) -> OqtopusJobResult:
        """Fetch one job by id and convert to typed SDK result.

        Args:
            job_id (Required): Target job ID to fetch.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        job = self._run_async_method(_AsyncOqtopusClient.get_job, job_id)
        return self._to_result(job)

    def get_job_result(self, job_id: str) -> OqtopusJobResult:
        """Alias of :meth:`get_job`.

        Args:
            job_id (Required): Target job ID to fetch.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self.get_job(job_id)

    def result(self, job_id: str) -> OqtopusJobResult:
        """Alias of :meth:`get_job_result`.

        Args:
            job_id (Required): Target job ID to fetch.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self.get_job_result(job_id)

    def refresh(self, job_id: str) -> OqtopusJobResult:
        """Alias of :meth:`get_job_result`.

        Args:
            job_id (Required): Target job ID to fetch.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self.get_job_result(job_id)

    def wait_for_job(  # noqa: PLR0913
        self,
        job_id: str,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusJobResult:
        """Poll one job until terminal status/timeout and return typed result.

        Args:
            job_id (Required): Target job ID to wait for.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an SDK result wrapper.

        """
        job = self._run_async_method(
            _AsyncOqtopusClient.wait_for_job,
            job_id,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )
        return self._to_result(job)

    def wait(  # noqa: PLR0913
        self,
        job_id: str,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
        on_status: Callable[[models.JobsGetJobStatusResponse], None] | None = None,
    ) -> OqtopusJobResult:
        """Alias of :meth:`wait_for_job`.

        Args:
            job_id (Required): Target job ID to wait for.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Statuses treated as terminal.
            failure_statuses (Optional): Statuses treated as failures.
            on_status (Optional): Callback invoked on each polled status.

        Returns:
            The finished job as an SDK result wrapper.

        """
        return self.wait_for_job(
            job_id,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
            on_status=on_status,
        )

    def wait_for_jobs(  # noqa: PLR0913
        self,
        job_ids: list[str],
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        max_workers: int = 4,
    ) -> list[OqtopusJobResult]:
        """Wait multiple jobs in parallel.

        Args:
            job_ids (Required): List of job IDs to wait for.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            max_workers (Optional): Waiting concurrency. Default is ``4``.

        Returns:
            Finished jobs as SDK result wrappers.

        Raises:
            ValueError: If ``max_workers`` is less than ``1``.

        """
        if max_workers < 1:
            msg = "max_workers must be >= 1."
            raise ValueError(msg)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(
                executor.map(
                    lambda job_id: self.wait_for_job(
                        job_id,
                        interval=interval,
                        interval_backoff=interval_backoff,
                        max_interval=max_interval,
                        timeout=timeout,
                    ),
                    job_ids,
                ),
            )

    async def wait_for_jobs_async(  # noqa: PLR0913
        self,
        job_ids: list[str],
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        max_workers: int = 4,
    ) -> list[OqtopusJobResult]:
        """Wait multiple jobs concurrently in an async context.

        Args:
            job_ids (Required): List of job IDs to wait for.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            max_workers (Optional): Waiting concurrency. Default is ``4``.

        Returns:
            Finished jobs as SDK result wrappers.

        Raises:
            ValueError: If ``max_workers`` is less than ``1``.

        """
        if max_workers < 1:
            msg = "max_workers must be >= 1."
            raise ValueError(msg)

        semaphore = asyncio.Semaphore(max_workers)

        async def _wait(job_id: str) -> OqtopusJobResult:
            async with semaphore:
                job = await self._run_async_with_client(
                    lambda async_client: async_client.wait_for_job(
                        job_id,
                        interval=interval,
                        interval_backoff=interval_backoff,
                        max_interval=max_interval,
                        timeout=timeout,
                    )
                )
                return self._to_result(job)

        return await asyncio.gather(*(_wait(job_id) for job_id in job_ids))

    def run_jobs_batch(  # noqa: PLR0913
        self,
        jobs: list[OqtopusJobSpec],
        *,
        submit_workers: int = 4,
        wait_workers: int = 4,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
    ) -> list[OqtopusJobResult]:
        """Submit multiple jobs, then wait for all of them.

        Args:
            jobs (Required): List of `OqtopusJobSpec`.
            submit_workers (Optional): Submission concurrency. Default is ``4``.
            wait_workers (Optional): Waiting concurrency. Default is ``4``.
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.

        Returns:
            Finished jobs as SDK result wrappers.

        Raises:
            TypeError: If any item in ``jobs`` is not an ``OqtopusJobSpec``.
            ValueError: If ``submit_workers`` is less than ``1``.

        """
        if submit_workers < 1:
            msg = "submit_workers must be >= 1."
            raise ValueError(msg)
        if any(not isinstance(job, OqtopusJobSpec) for job in jobs):
            msg = "run_jobs_batch expects a list of OqtopusJobSpec."
            raise TypeError(msg)
        submitted = self.submit_jobs(jobs, max_workers=submit_workers)
        return self.wait_for_jobs(
            [job.job_id for job in submitted],
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            max_workers=wait_workers,
        )

    def delete_job(self, job_id: str) -> models.SuccessSuccessResponse:
        """Delete a job by id.

        Args:
            job_id (Required): Target job ID to delete.

        Returns:
            Success response from the API.

        """
        return self._run_async_method(_AsyncOqtopusClient.delete_job, job_id)

    def get_job_status(self, job_id: str) -> models.JobsGetJobStatusResponse:
        """Get current status for one job.

        Args:
            job_id (Required): Target job ID to get status for.

        Returns:
            Raw job status response from the API.

        """
        return self._run_async_method(_AsyncOqtopusClient.get_job_status, job_id)

    def status(self, job_id: str) -> models.JobsJobStatus:
        """Get current job status enum for one job.

        Args:
            job_id (Required): Target job ID to get status for.

        Returns:
            The current job status.

        """
        return self.get_job_status(job_id).status

    def is_finished(
        self,
        job_id: str,
        *,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
    ) -> bool:
        """Return whether the job is in terminal status.

        Args:
            job_id (Required): Target job ID to inspect.
            terminal_statuses (Optional): Statuses treated as terminal. Defaults
                to ``succeeded``, ``failed``, and ``cancelled``.

        Returns:
            ``True`` when the job has reached a terminal status.

        """
        terminal = terminal_statuses or {
            models.JobsJobStatus.SUCCEEDED,
            models.JobsJobStatus.FAILED,
            models.JobsJobStatus.CANCELLED,
        }
        return self.status(job_id) in terminal

    def cancel_job(self, job_id: str) -> models.SuccessSuccessResponse:
        """Cancel a job by id.

        Args:
            job_id (Required): Target job ID to cancel.

        Returns:
            Success response from the API.

        """
        return self._run_async_method(_AsyncOqtopusClient.cancel_job, job_id)

    def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
        """Get encoded SSE log archive for one job.

        Args:
            job_id (Required): Target SSE job ID.

        Returns:
            Encoded SSE log archive response from the API.

        """
        return self._run_async_method(_AsyncOqtopusClient.get_sselog, job_id)

    def create_api_token(self) -> models.ApiTokenApiToken:
        """Create an API token.

        Returns:
            The created API token payload.

        """
        return self._run_async_method(_AsyncOqtopusClient.create_api_token)

    def get_api_token_status(self) -> models.ApiTokenApiTokenStatus:
        """Get API token status.

        Returns:
            The current API token status payload.

        """
        return self._run_async_method(_AsyncOqtopusClient.get_api_token_status)

    def get_api_token(self) -> models.ApiTokenApiTokenStatus:
        """Get API token status.

        Returns:
            The current API token status payload.

        """
        return self.get_api_token_status()

    def delete_api_token(self) -> None:
        """Delete current API token."""
        self._run_async_method(_AsyncOqtopusClient.delete_api_token)

    def get_announcements_list(
        self,
    ) -> models.AnnouncementsGetAnnouncementsListResponse:
        """List service announcements.

        Returns:
            Announcements list returned by the API.

        """
        return self._run_async_method(_AsyncOqtopusClient.get_announcements_list)

    def get_announcement(
        self, announcement_id: int
    ) -> models.AnnouncementsGetAnnouncementResponse:
        """Get one announcement by id.

        Args:
            announcement_id (Required): Target announcement ID.

        Returns:
            The requested announcement payload.

        """
        return self._run_async_method(
            _AsyncOqtopusClient.get_announcement, announcement_id
        )
