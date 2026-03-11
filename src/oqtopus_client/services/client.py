"""Core module for oqtopus-client."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import weakref
from collections.abc import Awaitable, Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import monotonic
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError
from typing_extensions import Self

from .. import rest as models
from ..rest.api.announcements_api import AnnouncementsApi
from ..rest.api.api_token_api import ApiTokenApi
from ..rest.api.device_api import DeviceApi
from ..rest.api.job_api import JobApi
from ..rest.api_client import ApiClient as RestApiClient
from ..rest.configuration import Configuration as RestConfiguration
from ..rest.exceptions import ApiException as RestApiException
from .config import OqtopusConfig
from .device import (
    OqtopusDevice,
)
from .errors import ResponseValidationError, UserApiError
from .job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from .job_spec import OqtopusJobSpec

PACKAGE_NAME = "oqtopus-client"
_SubmitJobInput = models.JobsSubmitJobRequest | Mapping[str, Any] | OqtopusJobSpec
_RunInput = _SubmitJobInput


def _resolve_user_agent() -> str:
    try:
        package_version = version(PACKAGE_NAME)
    except PackageNotFoundError:
        package_version = "unknown"
    return f"{PACKAGE_NAME}/{package_version}"


class _AsyncRuntime:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro: Any) -> Any:
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5.0)


class _AsyncOqtopusClient:
    def __init__(
        self,
        config: OqtopusConfig,
        default_headers: Mapping[str, str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        if not config.base_url and not self._is_sse_container():
            raise ValueError("config.base_url is required.")

        self.base_url = config.base_url.rstrip("/") if config.base_url else ""
        self._proxy = config.proxy
        self._headers: dict[str, str] = {
            "User-Agent": user_agent or _resolve_user_agent()
        }

        if config.retry_max_attempts < 1:
            raise ValueError("retry_max_attempts must be >= 1.")
        if config.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0.")
        self._retry_max_attempts = config.retry_max_attempts
        self._retry_backoff_seconds = config.retry_backoff_seconds
        self._retry_status_codes = set(
            config.retry_status_codes or {429, 500, 502, 503, 504}
        )
        self._retry_methods = {
            m.upper() for m in (config.retry_methods or {"GET", "DELETE"})
        }
        self._rest_timeout = config.timeout

        if default_headers:
            self._headers.update(default_headers)

        self._rest_config: RestConfiguration | None = None
        self._rest_client: RestApiClient | None = None
        self._job_api: JobApi | None = None
        self._device_api: DeviceApi | None = None
        self._token_api: ApiTokenApi | None = None
        self._announcements_api: AnnouncementsApi | None = None

        token = config.api_token
        if token:
            self._apply_api_token(token)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Defer REST API initialization until first API call.
            pass
        else:
            self._initialize_rest_api()

    def _apply_api_token(self, api_token: str) -> None:
        self._headers["q-api-token"] = api_token
        self._headers["Authorization"] = f"Bearer {api_token}"
        if self._rest_client is not None:  # pragma: no cover - integration path
            self._rest_client.set_default_header("q-api-token", api_token)
            self._rest_client.set_default_header(
                "Authorization", f"Bearer {api_token}"
            )
        if self._rest_config is not None:  # pragma: no cover - integration path
            self._rest_config.access_token = api_token

    def _initialize_rest_api(self) -> None:  # pragma: no cover - integration path
        if self._rest_client is not None:
            return
        rest_host = self.base_url or "http://localhost:8080"
        self._rest_config = RestConfiguration(host=rest_host)
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

    def _ensure_job_api(self) -> JobApi:
        if self._job_api is None:
            self._initialize_rest_api()
        if self._job_api is None:  # pragma: no cover - defensive guard
            msg = "Job API client is not initialized."
            raise RuntimeError(msg)
        return self._job_api

    def _ensure_device_api(self) -> DeviceApi:
        if self._device_api is None:
            self._initialize_rest_api()
        if self._device_api is None:  # pragma: no cover - defensive guard
            msg = "Device API client is not initialized."
            raise RuntimeError(msg)
        return self._device_api

    def _ensure_token_api(self) -> ApiTokenApi:
        if self._token_api is None:
            self._initialize_rest_api()
        if self._token_api is None:  # pragma: no cover - defensive guard
            msg = "API token client is not initialized."
            raise RuntimeError(msg)
        return self._token_api

    def _ensure_announcements_api(self) -> AnnouncementsApi:
        if self._announcements_api is None:
            self._initialize_rest_api()
        if self._announcements_api is None:  # pragma: no cover - defensive guard
            msg = "Announcements API client is not initialized."
            raise RuntimeError(msg)
        return self._announcements_api

    async def close(self) -> None:
        if self._rest_client is not None:  # pragma: no cover - integration path
            await self._rest_client.close()

    async def _call_rest(
        self, call: Awaitable[Any]
    ) -> Any:  # pragma: no cover - integration path
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
        job: models.JobsSubmitJobRequest | Mapping[str, Any] | OqtopusJobSpec,
    ) -> str | None:
        if isinstance(job, OqtopusJobSpec):
            spec_job_type = job.job_type
            if isinstance(spec_job_type, models.JobsJobType):
                return spec_job_type.value
            if isinstance(spec_job_type, str):
                return spec_job_type
            return None
        if isinstance(job, models.JobsSubmitJobRequest):
            return job.job_type.value
        mapping_job_type = job.get("job_type")
        if isinstance(mapping_job_type, models.JobsJobType):
            return mapping_job_type.value
        if isinstance(mapping_job_type, str):
            return mapping_job_type
        return None

    @staticmethod
    def _coerce_submit_job_request(
        job: _RunInput,
    ) -> models.JobsSubmitJobRequest:
        if isinstance(job, models.JobsSubmitJobRequest):
            return job
        if isinstance(job, OqtopusJobSpec):
            return job.to_model()
        return models.JobsSubmitJobRequest.model_validate(dict(job))

    @classmethod
    def _validate_run_job_type(
        cls,
        job: models.JobsSubmitJobRequest | Mapping[str, Any] | OqtopusJobSpec,
        expected: models.JobsJobType,
    ) -> None:
        actual = cls._job_type_of(job)
        if actual != expected.value:
            raise ValueError(
                f"job_type must be '{expected.value}' for this helper (got {actual!r})."
            )

    @staticmethod
    def _extract_error_message(payload: Any) -> str | None:
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

    async def _run_sse_container_job(
        self,
        request: models.JobsSubmitJobRequest,
    ) -> models.JobsJobDef:
        try:
            sse_sampler = import_module("sse_sampler")
        except ModuleNotFoundError as exc:
            raise UserApiError(
                0,
                "sse_container mode requires 'sse_sampler' module.",
                payload={"mode": "sse_container"},
            ) from exc

        try:
            response = sse_sampler.req_transpile_and_exec(  # type: ignore[attr-defined]
                request.job_info.program,
                request.shots,
                request.transpiler_info or {},
            )
        except Exception as exc:  # pragma: no cover - surfaced as API error
            raise UserApiError(
                0,
                f"sse_container execution failed: {exc}",
                payload={"mode": "sse_container", "job_type": request.job_type.value},
            ) from exc

        response_payload: Any = response
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

        try:
            return TypeAdapter(models.JobsJobDef).validate_python(response_payload)
        except ValidationError as exc:
            try:
                return models.JobsJobDef.model_validate(response, from_attributes=True)
            except ValidationError:  # pragma: no cover
                raise ResponseValidationError(str(exc), response_payload) from exc

    async def list_devices(self) -> list[models.DevicesDeviceInfo]:
        device_api = self._ensure_device_api()
        return cast(
            "list[models.DevicesDeviceInfo]",
            await self._call_rest(
                device_api.list_devices(_request_timeout=self._rest_timeout)
            ),
        )

    async def get_device(self, device_id: str) -> models.DevicesDeviceInfo:
        device_api = self._ensure_device_api()
        return cast(
            "models.DevicesDeviceInfo",
            await self._call_rest(
                device_api.get_device(
                    device_id,
                    _request_timeout=self._rest_timeout,
                )
            ),
        )

    async def list_jobs(
        self,
        *,
        fields: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        q: str | None = None,
        page: int | None = None,
        size: int | None = None,
        order: str | None = None,
    ) -> list[models.JobsGetJobsResponse]:
        job_api = self._ensure_job_api()
        return cast(
            "list[models.JobsGetJobsResponse]",
            await self._call_rest(
                job_api.list_jobs(
                    fields=fields,
                    start_time=start_time,
                    end_tiime=end_time,
                    q=q,
                    page=page,
                    size=size,
                    order=order,
                    _request_timeout=self._rest_timeout,
                ),
            ),
        )

    async def submit_job(self, body: _SubmitJobInput) -> models.JobsSubmitJobResponse:
        payload: models.JobsSubmitJobRequest | dict[str, Any]
        if isinstance(body, OqtopusJobSpec):
            payload = body.to_model()
        elif isinstance(body, models.JobsSubmitJobRequest):
            payload = body
        else:
            payload = dict(body)
        job_api = self._ensure_job_api()
        request = (
            payload
            if isinstance(payload, models.JobsSubmitJobRequest)
            else models.JobsSubmitJobRequest.model_validate(payload)
        )
        return cast(
            "models.JobsSubmitJobResponse",
            await self._call_rest(
                job_api.submit_job(request, _request_timeout=self._rest_timeout)
            ),
        )

    async def run_job(self, job: _SubmitJobInput, **kwargs: Any) -> models.JobsJobDef:
        request = self._coerce_submit_job_request(job)
        if self._is_sse_container():
            if request.job_type in {
                models.JobsJobType.SAMPLING,
                models.JobsJobType.MULTI_MANUAL,
                models.JobsJobType.SSE,
            }:
                return await self._run_sse_container_job(request)
            raise UserApiError(  # pragma: no cover - defensive branch
                0,
                (
                    f"job_type '{request.job_type.value}' is not supported in "
                    "sse_container mode."
                ),
                payload={"mode": "sse_container", "job_type": request.job_type.value},
            )

        response = await self.submit_job(request)
        return await self.wait_for_job(response.job_id, **kwargs)

    async def run_sampling(self, job: _RunInput, **kwargs: Any) -> models.JobsJobDef:
        request = self._coerce_submit_job_request(job)
        self._validate_run_job_type(request, models.JobsJobType.SAMPLING)
        return await self.run_job(request, **kwargs)

    async def run_estimation(self, job: _RunInput, **kwargs: Any) -> models.JobsJobDef:
        request = self._coerce_submit_job_request(job)
        self._validate_run_job_type(request, models.JobsJobType.ESTIMATION)
        return await self.run_job(request, **kwargs)

    async def run_multi_manual(
        self, job: _RunInput, **kwargs: Any
    ) -> models.JobsJobDef:
        request = self._coerce_submit_job_request(job)
        self._validate_run_job_type(request, models.JobsJobType.MULTI_MANUAL)
        return await self.run_job(request, **kwargs)

    async def run_sse(self, job: _RunInput, **kwargs: Any) -> models.JobsJobDef:
        request = self._coerce_submit_job_request(job)
        self._validate_run_job_type(request, models.JobsJobType.SSE)
        return await self.run_job(request, **kwargs)

    @staticmethod
    def build_sse_job_request(
        file_path: str | Path,
        *,
        device_id: str,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict[str, Any] | None = None,
        simulator_info: dict[str, Any] | None = None,
        mitigation_info: dict[str, Any] | None = None,
        shots: int = 1,
        max_encoded_file_size: int = 10 * 1024 * 1024,
    ) -> models.JobsSubmitJobRequest:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"The file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"The path is not a file: {path}")
        if path.suffix != ".py":
            raise ValueError(f"The file is not python file: {path}")

        encoded = base64.b64encode(path.read_bytes())
        if len(encoded) >= max_encoded_file_size:
            raise ValueError(
                "size of the base64 encoded file is larger than "
                f"{max_encoded_file_size}"
            )

        return models.JobsSubmitJobRequest(
            name=name,
            description=description,
            device_id=device_id,
            job_type=models.JobsJobType.SSE,
            job_info=models.JobsSubmitJobInfo(program=[encoded.decode("utf-8")]),
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            shots=shots,
        )

    async def run_sse_file(
        self, *, file_path: str | Path, device_id: str, **kwargs: Any
    ) -> models.JobsJobDef:
        request = self.build_sse_job_request(
            file_path=file_path,
            device_id=device_id,
            name=kwargs.pop("name", None),
            description=kwargs.pop("description", None),
            transpiler_info=kwargs.pop("transpiler_info", None),
            simulator_info=kwargs.pop("simulator_info", None),
            mitigation_info=kwargs.pop("mitigation_info", None),
            shots=kwargs.pop("shots", 1),
            max_encoded_file_size=kwargs.pop("max_encoded_file_size", 10 * 1024 * 1024),
        )
        return await self.run_sse(request, **kwargs)

    async def get_job(self, job_id: str) -> models.JobsJobDef:
        job_api = self._ensure_job_api()
        return cast(
            "models.JobsJobDef",
            await self._call_rest(
                job_api.get_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def wait_for_job(
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
    ) -> models.JobsJobDef:
        if interval <= 0:
            raise ValueError("interval must be greater than 0.")
        if interval_backoff < 1.0:
            raise ValueError("interval_backoff must be >= 1.0.")
        if max_interval is not None and max_interval <= 0:
            raise ValueError("max_interval must be greater than 0 or None.")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be greater than 0 or None.")

        terminal = terminal_statuses or {
            models.JobsJobStatus.SUCCEEDED,
            models.JobsJobStatus.FAILED,
            models.JobsJobStatus.CANCELLED,
        }
        failed = failure_statuses or {
            models.JobsJobStatus.FAILED,
            models.JobsJobStatus.CANCELLED,
        }

        deadline = monotonic() + timeout if timeout is not None else None
        next_interval = interval

        while True:
            status_response = await self.get_job_status(job_id)
            if on_status is not None:
                on_status(status_response)
            current = status_response.status
            if current in terminal:
                job = await self.get_job(job_id)
                if current in failed:
                    raise UserApiError(
                        0,
                        f"job {job_id} finished with status '{current.value}'",
                        payload={"job_id": job_id, "status": current.value},
                    )
                return job

            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for job {job_id} after {timeout} seconds."
                )

            sleep_for = next_interval
            if deadline is not None:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"Timed out waiting for job {job_id} after {timeout} seconds."
                    )
                sleep_for = min(sleep_for, remaining)

            await asyncio.sleep(sleep_for)
            next_interval *= interval_backoff
            if max_interval is not None:
                next_interval = min(next_interval, max_interval)

    async def delete_job(self, job_id: str) -> models.SuccessSuccessResponse:
        job_api = self._ensure_job_api()
        return cast(
            "models.SuccessSuccessResponse",
            await self._call_rest(
                job_api.delete_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def get_job_status(self, job_id: str) -> models.JobsGetJobStatusResponse:
        job_api = self._ensure_job_api()
        return cast(
            "models.JobsGetJobStatusResponse",
            await self._call_rest(
                job_api.get_job_status(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def cancel_job(self, job_id: str) -> models.SuccessSuccessResponse:
        job_api = self._ensure_job_api()
        return cast(
            "models.SuccessSuccessResponse",
            await self._call_rest(
                job_api.cancel_job(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def get_sselog(self, job_id: str) -> models.JobsGetSselogResponse:
        job_api = self._ensure_job_api()
        return cast(
            "models.JobsGetSselogResponse",
            await self._call_rest(
                job_api.get_sselog(job_id, _request_timeout=self._rest_timeout)
            ),
        )

    async def create_api_token(self) -> models.ApiTokenApiToken:
        token_api = self._ensure_token_api()
        token = cast(
            "models.ApiTokenApiToken",
            await self._call_rest(
                token_api.create_api_token(_request_timeout=self._rest_timeout)
            ),
        )
        if token is None:  # pragma: no cover
            raise ResponseValidationError("create_api_token response is empty.", token)
        return token

    async def get_api_token(self) -> models.ApiTokenApiToken:
        token_api = self._ensure_token_api()
        return cast(
            "models.ApiTokenApiToken",
            await self._call_rest(
                token_api.get_api_token(_request_timeout=self._rest_timeout)
            ),
        )

    async def delete_api_token(self) -> None:
        token_api = self._ensure_token_api()
        await self._call_rest(
            token_api.delete_api_token(_request_timeout=self._rest_timeout)
        )

    async def get_announcements_list(
        self,
    ) -> models.AnnouncementsGetAnnouncementsListResponse:
        announcements_api = self._ensure_announcements_api()
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
        announcements_api = self._ensure_announcements_api()
        return cast(
            "models.AnnouncementsGetAnnouncementResponse",
            await self._call_rest(
                announcements_api.get_announcement(
                    announcement_id, _request_timeout=self._rest_timeout
                )
            ),
        )


class OqtopusClient:
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
                `OqtopusConfig.from_file()` is used. If the resolved config has an
                empty `base_url`, the internal REST client falls back to
                `http://localhost:8080`, which matches the default local
                OQTOPUS Cloud port.
            default_headers (Optional): Additional headers merged into every
                request.
            user_agent (Optional): Custom User-Agent header value.

        """
        resolved_config = config or OqtopusConfig.from_file()
        self._runtime = _AsyncRuntime()
        try:
            self._async = self._runtime.run(
                asyncio.sleep(
                    0,
                    result=_AsyncOqtopusClient(
                        config=resolved_config,
                        default_headers=default_headers,
                        user_agent=user_agent,
                    ),
                )
            )
        except Exception:
            with suppress(Exception):
                self._runtime.close()
            raise
        self._closed = False
        self._finalizer = weakref.finalize(
            self, self._finalize_resources, self._runtime, self._async
        )
        self.base_url = self._async.base_url
        self.timeout = resolved_config.timeout
        self.retry_max_attempts = resolved_config.retry_max_attempts
        self.retry_backoff_seconds = resolved_config.retry_backoff_seconds
        self.retry_status_codes = frozenset(
            resolved_config.retry_status_codes or {429, 500, 502, 503, 504}
        )
        self.retry_methods = frozenset(
            m.upper() for m in (resolved_config.retry_methods or {"GET", "DELETE"})
        )

    @staticmethod
    def _finalize_resources(
        runtime: _AsyncRuntime, async_client: _AsyncOqtopusClient
    ) -> None:
        with suppress(Exception):
            runtime.run(async_client.close())
        with suppress(Exception):
            runtime.close()

    def _call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        if self._closed:
            raise RuntimeError("Client is closed.")

        async def _run() -> Any:
            method = getattr(self._async, method_name)
            return await method(*args, **kwargs)

        return self._runtime.run(_run())

    def _to_result(self, job: models.JobsJobDef) -> OqtopusJobResult:
        raw = job.job_info.result if job.job_info is not None else None
        transpile_result = (
            job.job_info.transpile_result if job.job_info is not None else None
        )
        message = job.job_info.message if job.job_info is not None else None
        if job.job_type == models.JobsJobType.MULTI_MANUAL:
            return OqtopusMultiManualJobResult(
                raw,
                job_id=job.job_id,
                job_type=job.job_type,
                status=job.status,
                name=job.name,
                description=job.description,
                device_id=job.device_id,
                shots=job.shots,
                job_info=job.job_info,
                transpiler_info=job.transpiler_info,
                simulator_info=job.simulator_info,
                mitigation_info=job.mitigation_info,
                transpile_result=transpile_result,
                message=message,
                execution_time=job.execution_time,
                submitted_at=job.submitted_at,
                ready_at=job.ready_at,
                running_at=job.running_at,
                ended_at=job.ended_at,
                client=self,
            )
        if job.job_type == models.JobsJobType.SSE:
            return OqtopusSseJobResult(
                raw,
                job_id=job.job_id,
                job_type=job.job_type,
                status=job.status,
                name=job.name,
                description=job.description,
                device_id=job.device_id,
                shots=job.shots,
                job_info=job.job_info,
                transpiler_info=job.transpiler_info,
                simulator_info=job.simulator_info,
                mitigation_info=job.mitigation_info,
                transpile_result=transpile_result,
                message=message,
                execution_time=job.execution_time,
                submitted_at=job.submitted_at,
                ready_at=job.ready_at,
                running_at=job.running_at,
                ended_at=job.ended_at,
                client=self,
            )
        if job.job_type == models.JobsJobType.SAMPLING:
            return OqtopusSamplingJobResult(
                raw,
                job_id=job.job_id,
                job_type=job.job_type,
                status=job.status,
                name=job.name,
                description=job.description,
                device_id=job.device_id,
                shots=job.shots,
                job_info=job.job_info,
                transpiler_info=job.transpiler_info,
                simulator_info=job.simulator_info,
                mitigation_info=job.mitigation_info,
                transpile_result=transpile_result,
                message=message,
                execution_time=job.execution_time,
                submitted_at=job.submitted_at,
                ready_at=job.ready_at,
                running_at=job.running_at,
                ended_at=job.ended_at,
                client=self,
            )
        if job.job_type == models.JobsJobType.ESTIMATION:
            return OqtopusEstimationJobResult(
                raw,
                job_id=job.job_id,
                job_type=job.job_type,
                status=job.status,
                name=job.name,
                description=job.description,
                device_id=job.device_id,
                shots=job.shots,
                job_info=job.job_info,
                transpiler_info=job.transpiler_info,
                simulator_info=job.simulator_info,
                mitigation_info=job.mitigation_info,
                transpile_result=transpile_result,
                message=message,
                execution_time=job.execution_time,
                submitted_at=job.submitted_at,
                ready_at=job.ready_at,
                running_at=job.running_at,
                ended_at=job.ended_at,
                client=self,
            )
        return OqtopusJobResult(
            raw,
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            name=job.name,
            description=job.description,
            device_id=job.device_id,
            shots=job.shots,
            job_info=job.job_info,
            transpiler_info=job.transpiler_info,
            simulator_info=job.simulator_info,
            mitigation_info=job.mitigation_info,
            transpile_result=transpile_result,
            message=message,
            execution_time=job.execution_time,
            submitted_at=job.submitted_at,
            ready_at=job.ready_at,
            running_at=job.running_at,
            ended_at=job.ended_at,
            client=self,
        )  # pragma: no cover

    @staticmethod
    def _to_device(device: models.DevicesDeviceInfo) -> OqtopusDevice:
        return OqtopusDevice(raw=device)

    def __enter__(self) -> Self:
        """Enter the client context.

        Returns:
            The client instance itself.

        """
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Exit context manager and close internal resources."""
        self.close()

    def close(self) -> None:
        """Close underlying async HTTP client."""
        if self._closed:
            return
        if self._finalizer.alive:
            self._finalizer()
        self._closed = True

    def list_devices(self) -> list[OqtopusDevice]:
        """List available devices.

        Returns:
            Available devices wrapped as SDK device objects.

        """
        return [self._to_device(device) for device in self._call("list_devices")]

    def get_device(self, device_id: str) -> OqtopusDevice:
        """Get one device by id.

        Returns:
            The requested device wrapped as an SDK device object.

        """
        return self._to_device(self._call("get_device", device_id))

    def list_jobs(self, **kwargs: Any) -> list[models.JobsGetJobsResponse]:
        """List jobs with optional filters.

        Returns:
            Jobs returned by the API.

        """
        return self._call("list_jobs", **kwargs)

    def submit_job(self, body: OqtopusJobSpec) -> models.JobsSubmitJobResponse:
        """Submit one job and return submission response.

        Args:
            body (Required): `OqtopusJobSpec`.

        Returns:
            Submission response for the created job.

        Raises:
            TypeError: If ``body`` is not an ``OqtopusJobSpec``.

        """
        if not isinstance(body, OqtopusJobSpec):
            raise TypeError("submit_job expects OqtopusJobSpec.")  # pragma: no cover
        return self._call("submit_job", body)

    def submit_jobs(
        self,
        jobs: Sequence[OqtopusJobSpec],
        *,
        max_workers: int = 4,
    ) -> list[models.JobsSubmitJobResponse]:
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
            raise ValueError("max_workers must be >= 1.")
        if any(not isinstance(job, OqtopusJobSpec) for job in jobs):
            raise TypeError(
                "submit_jobs expects a list of OqtopusJobSpec."
            )  # pragma: no cover
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(self.submit_job, jobs))

    @staticmethod
    def _ensure_job_spec(
        job: OqtopusJobSpec,
        *,
        expected: models.JobsJobType | None = None,
        method: str = "run_job",
    ) -> OqtopusJobSpec:
        if not isinstance(job, OqtopusJobSpec):
            raise TypeError(f"{method} expects OqtopusJobSpec.")  # pragma: no cover
        if expected is not None and models.JobsJobType(job.job_type) != expected:
            raise ValueError(
                f"job.job_type must be '{expected.value}' for {method} "
                f"(got {job.job_type!r})."
            )
        return job

    def run_job(self, job: OqtopusJobSpec, **kwargs: Any) -> OqtopusJobResult:
        """Submit one job spec, wait until completion, and return typed result.

        Args:
            job (Required): `OqtopusJobSpec`.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as an SDK result wrapper.

        """
        spec = self._ensure_job_spec(job, method="run_job")
        finished_job = self._call("run_job", spec.to_model(), **kwargs)
        return self._to_result(finished_job)

    def run_sampling(
        self, job: OqtopusJobSpec, **kwargs: Any
    ) -> OqtopusSamplingJobResult:
        """Run a sampling job and return sampling-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='sampling'``.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as a sampling result wrapper.

        Raises:
            ResponseValidationError: If the API response is not a sampling result.

        """
        spec = self._ensure_job_spec(
            job, expected=models.JobsJobType.SAMPLING, method="run_sampling"
        )
        finished_job = self._call(
            "run_sampling", spec.to_model(), **kwargs
        )
        result = self._to_result(finished_job)
        if not isinstance(result, OqtopusSamplingJobResult):
            raise ResponseValidationError(
                "run_sampling returned non-sampling job result",
                finished_job.model_dump(),
            )  # pragma: no cover
        return cast("OqtopusSamplingJobResult", result)

    def run_estimation(
        self, job: OqtopusJobSpec, **kwargs: Any
    ) -> OqtopusEstimationJobResult:
        """Run an estimation job and return estimation-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='estimation'``.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as an estimation result wrapper.

        Raises:
            ResponseValidationError: If the API response is not an estimation result.

        """
        spec = self._ensure_job_spec(
            job, expected=models.JobsJobType.ESTIMATION, method="run_estimation"
        )
        finished_job = self._call(
            "run_estimation", spec.to_model(), **kwargs
        )
        result = self._to_result(finished_job)
        if not isinstance(result, OqtopusEstimationJobResult):
            raise ResponseValidationError(
                "run_estimation returned non-estimation job result",
                finished_job.model_dump(),
            )  # pragma: no cover
        return cast("OqtopusEstimationJobResult", result)

    def run_multi_manual(
        self, job: OqtopusJobSpec, **kwargs: Any
    ) -> OqtopusMultiManualJobResult:
        """Run a multi-manual job and return multi-manual-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='multi_manual'``.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as a multi-manual result wrapper.

        Raises:
            ResponseValidationError: If the API response is not a multi-manual result.

        """
        spec = self._ensure_job_spec(
            job, expected=models.JobsJobType.MULTI_MANUAL, method="run_multi_manual"
        )
        finished_job = self._call(
            "run_multi_manual", spec.to_model(), **kwargs
        )
        result = self._to_result(finished_job)
        if not isinstance(result, OqtopusMultiManualJobResult):
            raise ResponseValidationError(
                "run_multi_manual returned non-multi_manual job result",
                finished_job.model_dump(),
            )  # pragma: no cover
        return cast("OqtopusMultiManualJobResult", result)

    def run_sse(self, job: OqtopusJobSpec, **kwargs: Any) -> OqtopusSseJobResult:
        """Run an SSE job and return SSE-typed SDK result.

        Args:
            job (Required): `OqtopusJobSpec` with ``job_type='sse'``.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as an SSE result wrapper.

        Raises:
            ResponseValidationError: If the API response is not an SSE result.

        """
        spec = self._ensure_job_spec(
            job, expected=models.JobsJobType.SSE, method="run_sse"
        )
        finished_job = self._call("run_sse", spec.to_model(), **kwargs)
        result = self._to_result(finished_job)
        if not isinstance(result, OqtopusSseJobResult):
            raise ResponseValidationError(
                "run_sse returned non-sse job result",
                finished_job.model_dump(),
            )  # pragma: no cover
        return cast("OqtopusSseJobResult", result)

    def run_sse_file(
        self, *, file_path: str | Path, device_id: str, **kwargs: Any
    ) -> OqtopusSseJobResult:
        """Build and run an SSE job directly from a script file and return SSE result.

        Args:
            file_path (Required): Path to the Python script.
            device_id (Required): Target device ID.
            kwargs (Optional): ``name``, ``description``, ``shots``, ``interval``,
                ``interval_backoff``, ``max_interval``, ``timeout``,
                ``terminal_statuses``, ``failure_statuses``.

        Returns:
            The finished job as an SSE result wrapper.

        Raises:
            ResponseValidationError: If the API response is not an SSE result.

        """
        finished_job = self._call(
            "run_sse_file", file_path=file_path, device_id=device_id, **kwargs
        )
        result = self._to_result(finished_job)
        if not isinstance(result, OqtopusSseJobResult):
            raise ResponseValidationError(
                "run_sse_file returned non-sse job result", finished_job.model_dump()
            )  # pragma: no cover
        return cast("OqtopusSseJobResult", result)

    def get_job(self, job_id: str) -> OqtopusJobResult:
        """Fetch one job by id and convert to typed SDK result.

        Args:
            job_id (Required): Target job ID to fetch.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self._to_result(self._call("get_job", job_id))

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

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self.get_job_result(job_id)

    def refresh(self, job_id: str) -> OqtopusJobResult:
        """Alias of :meth:`get_job_result`.

        Returns:
            The fetched job as an SDK result wrapper.

        """
        return self.get_job_result(job_id)

    def wait_for_job(self, job_id: str, **kwargs: Any) -> OqtopusJobResult:
        """Poll one job until terminal status/timeout and return typed result.

        Args:
            job_id (Required): Target job ID to wait for.
            kwargs (Optional): ``interval``, ``interval_backoff``,
                ``max_interval``, ``timeout``, ``terminal_statuses``,
                ``failure_statuses``.

        Returns:
            The finished job as an SDK result wrapper.

        """
        return self._to_result(self._call("wait_for_job", job_id, **kwargs))

    def wait(self, job_id: str, **kwargs: Any) -> OqtopusJobResult:
        """Alias of :meth:`wait_for_job`.

        Returns:
            The finished job as an SDK result wrapper.

        """
        return self.wait_for_job(job_id, **kwargs)

    def wait_for_jobs(
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
            raise ValueError("max_workers must be >= 1.")
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

    def run_jobs_batch(
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
            raise ValueError("submit_workers must be >= 1.")
        if any(not isinstance(job, OqtopusJobSpec) for job in jobs):
            raise TypeError("run_jobs_batch expects a list of OqtopusJobSpec.")
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
        return self._call("delete_job", job_id)

    def get_job_status(self, job_id: str) -> models.JobsGetJobStatusResponse:
        """Get current status for one job.

        Args:
            job_id (Required): Target job ID to get status for.

        Returns:
            Raw job status response from the API.

        """
        return self._call("get_job_status", job_id)

    def status(self, job_id: str) -> models.JobsJobStatus:
        """Get current job status enum for one job.

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
        return self._call("cancel_job", job_id)

    def get_sselog(self, job_id: str) -> models.JobsGetSselogResponse:
        """Get encoded SSE log archive for one job.

        Returns:
            Encoded SSE log archive response from the API.

        """
        return self._call("get_sselog", job_id)

    def create_api_token(self) -> models.ApiTokenApiToken:
        """Create an API token.

        Returns:
            The created API token payload.

        """
        return self._call("create_api_token")

    def get_api_token(self) -> models.ApiTokenApiToken:
        """Get API token.

        Returns:
            The current API token payload.

        """
        return self._call("get_api_token")

    def delete_api_token(self) -> None:
        """Delete current API token."""
        self._call("delete_api_token")

    def get_announcements_list(
        self,
    ) -> models.AnnouncementsGetAnnouncementsListResponse:
        """List service announcements.

        Returns:
            Announcements list returned by the API.

        """
        return self._call("get_announcements_list")

    def get_announcement(
        self, announcement_id: int
    ) -> models.AnnouncementsGetAnnouncementResponse:
        """Get one announcement by id.

        Returns:
            The requested announcement payload.

        """
        return self._call("get_announcement", announcement_id)
