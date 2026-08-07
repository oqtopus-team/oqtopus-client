"""Unit tests for oqtopus-client."""

from __future__ import annotations

import asyncio
import base64
import importlib
import sys
import threading
import types
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeVar, cast

import pytest

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusDevice,
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusJobSpec,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
    UserApiError,
)
from oqtopus_client import (
    rest as models,
)
from oqtopus_client.rest.models.jobs_get_sselog_response import JobsGetSselogResponse
from oqtopus_client.services.client import (
    _AsyncOqtopusClient,
    _resolve_user_agent,
)

_T = TypeVar("_T")


def _run_with_async_client(
    config: OqtopusConfig,
    callback: Callable[[_AsyncOqtopusClient], Coroutine[object, object, _T]],
    *,
    default_headers: dict[str, str] | None = None,
) -> _T:
    async def _scenario() -> _T:
        client = _AsyncOqtopusClient(
            config,
            default_headers,
            None,
        )
        try:
            return await callback(client)
        finally:
            await client.close()

    return asyncio.run(_scenario())


def test_removed_compatibility_module_import_fails() -> None:
    """Test case: test_removed_compatibility_module_import_fails."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("oqtopus_client.client")


def _job(
    job_type: models.JobsJobType,
    *,
    status: models.JobsJobStatus = models.JobsJobStatus.SUCCEEDED,
) -> models.JobsJob:
    result: models.JobsS3JobResult
    if job_type == models.JobsJobType.ESTIMATION:
        result = models.JobsS3JobResult(
            estimation=models.JobsS3EstimationResult(exp_value=1.0, stds=0.1)
        )
    else:
        result = models.JobsS3JobResult(
            sampling=models.JobsS3SamplingResult(counts={"00": 1})
        )
    return models.JobsJob(
        job_id="job-1",
        name="job",
        job_type=job_type,
        status=status,
        device_id="K",
        shots=1,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["x"]),
            result=result,
        ),
    )


def test_resolve_user_agent_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_resolve_user_agent_falls_back_to_unknown."""
    monkeypatch.setattr(
        "oqtopus_client.services.client.version",
        lambda _: (_ for _ in ()).throw(PackageNotFoundError()),
    )
    assert _resolve_user_agent().endswith("unknown")


def test_async_client_constructor_validation_errors() -> None:
    """Test case: test_async_client_constructor_validation_errors."""
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url=""))
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url="http://test", retry_max_attempts=0))
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url="http://test", retry_backoff_seconds=-1))


def test_async_client_allows_empty_base_url_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_async_client_allows_empty_base_url_in_sse_container."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")

    async def _assert(client: _AsyncOqtopusClient) -> None:
        assert client.base_url == ""

    _run_with_async_client(OqtopusConfig(base_url=""), _assert)


def test_async_client_sets_headers_and_rest_config() -> None:
    """Test case: test_async_client_sets_headers_and_rest_config."""
    async def _assert(client: _AsyncOqtopusClient) -> None:
        assert client._headers["q-api-token"] == "from-config"
        assert client._headers["X-Test"] == "1"
        assert client._rest_config is not None
        assert client._rest_config.host == "http://test"
        assert client._rest_config.proxy == "http://proxy.local:8080"
        assert client._retry_status_codes == {429}

    _run_with_async_client(
        OqtopusConfig(
            base_url="http://test",
            api_token="from-config",
            proxy="http://proxy.local:8080",
        ),
        _assert,
        default_headers={"X-Test": "1"},
    )


def test_extract_error_message_variants() -> None:
    """Test case: test_extract_error_message_variants."""
    assert _AsyncOqtopusClient._extract_error_message({"message": "m"}) == "m"
    assert _AsyncOqtopusClient._extract_error_message({"error": "e"}) == "e"
    assert _AsyncOqtopusClient._extract_error_message({"error": {"message": "deep"}}) == "deep"
    assert _AsyncOqtopusClient._extract_error_message(" text ") == "text"
    assert _AsyncOqtopusClient._extract_error_message({}) is None


def test_coerce_and_validate_job_type() -> None:
    """Test case: test_coerce_and_validate_job_type."""
    req = _AsyncOqtopusClient._to_submit_job_request(
        OqtopusJobSpec.sampling(device_id="K", program="x"),
    )
    assert req.job_type == models.JobsJobType.SAMPLING

    _AsyncOqtopusClient._validate_run_job_type(req, models.JobsJobType.SAMPLING)
    with pytest.raises(ValueError):
        _AsyncOqtopusClient._validate_run_job_type(req, models.JobsJobType.ESTIMATION)


def test_wait_for_job_failure_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_wait_for_job_failure_and_timeout."""
    async def _assert(client: _AsyncOqtopusClient) -> None:
        async def status_failed(_: str) -> models.JobsGetJobStatusResponse:
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.FAILED)

        async def status_running(_: str) -> models.JobsGetJobStatusResponse:
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.RUNNING)

        async def get_job(_: str) -> models.JobsJob:
            return _job(models.JobsJobType.SAMPLING, status=models.JobsJobStatus.FAILED)

        monkeypatch.setattr(client, "get_job_status", status_failed)
        monkeypatch.setattr(client, "get_job", get_job)
        result = await client.wait_for_job("job-1", interval=0.001, timeout=0.01)
        assert result.status == models.JobsJobStatus.FAILED

        monkeypatch.setattr(client, "get_job_status", status_running)
        with pytest.raises(TimeoutError):
            await client.wait_for_job("job-1", interval=0.001, timeout=0.01)

    _run_with_async_client(OqtopusConfig(base_url="http://test"), _assert)


def test_run_sse_file_forwards_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_sse_file_forwards_kwargs."""
    script = tmp_path / "job.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    observed: dict[str, Any] = {}

    def build_stub(
        *, file_path: str | Path, device_id: str, **kwargs: Any
    ) -> OqtopusJobSpec:
        observed["build"] = {"file_path": str(file_path), "device_id": device_id, **kwargs}
        return OqtopusJobSpec.sse(
            device_id=device_id,
            shots=1,
            program="print('ok')\n",
        )

    async def run_sse_stub(
        self: _AsyncOqtopusClient, job: Any, **kwargs: Any
    ) -> models.JobsJob:
        observed["run"] = {"job": job, "kwargs": kwargs}
        return _job(models.JobsJobType.SSE)

    monkeypatch.setattr(_AsyncOqtopusClient, "build_sse_job_request", staticmethod(build_stub))
    monkeypatch.setattr(_AsyncOqtopusClient, "run_sse", run_sse_stub)

    async def _assert(client: _AsyncOqtopusClient) -> None:
        result = await client.run_sse_file(
            file_path=script,
            device_id="K",
            name="n",
            description="d",
            timeout=5.0,
            shots=3,
        )
        assert result.job_type == models.JobsJobType.SSE
        assert observed["build"]["device_id"] == "K"
        assert observed["run"]["kwargs"]["timeout"] == 5.0

    _run_with_async_client(OqtopusConfig(base_url="http://test"), _assert)


def test_build_sse_job_request_uses_sse_program(tmp_path: Path) -> None:
    """Test case: test_build_sse_job_request_uses_sse_program."""
    script = tmp_path / "job.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    request = _AsyncOqtopusClient.build_sse_job_request(
        file_path=script,
        device_id="K",
    )

    payload = request.to_s3_submit_job_info()
    assert payload.sse_program == "print('ok')\n"
    assert payload.program is None


def test_run_job_uses_sse_driver_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_job_uses_sse_driver_in_sse_container."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    loop_thread_id = threading.get_ident()
    observed: dict[str, int] = {}

    def submit_job(
        input_job: models.JobsSubmitJobRequest, upload_info: models.JobsS3SubmitJobInfo,
    ) -> dict[str, Any]:
        observed["thread_id"] = threading.get_ident()
        return {
            "job_id": "job-sse-container",
            "name": "job",
            "job_type": "sampling",
            "status": "succeeded",
            "device_id": "sse",
            "shots": input_job.shots,
            "job_info": {
                "input": {"program": upload_info.program},
                "result": {"sampling": {"counts": {"00": 1}}},
            },
        }

    fake_module = types.SimpleNamespace(
        submit_job=submit_job,
    )
    monkeypatch.setitem(sys.modules, "sse_driver", fake_module)

    async def _assert(client: _AsyncOqtopusClient) -> None:
        result = await client.run_job(
            OqtopusJobSpec.sampling(device_id="sse", program="OPENQASM 3; qubit[1] q;"),
        )
        assert result.job_id == "job-sse-container"

    _run_with_async_client(OqtopusConfig(base_url=""), _assert)
    assert observed["thread_id"] != loop_thread_id


def test_run_job_normalizes_flat_sse_container_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_run_job_normalizes_flat_sse_container_response."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")

    def submit_job(
        input_job: models.JobsSubmitJobRequest, upload_info: models.JobsS3SubmitJobInfo,
    ) -> dict[str, Any]:
        return {
            "job_id": "job-sse-flat",
            "name": "job",
            "job_type": "sampling",
            "status": "succeeded",
            "device_id": "sse",
            "shots": input_job.shots,
            "input": {"program": upload_info.program},
            "result": {"sampling": {"counts": {"00": 1}}},
            "transpile_result": {"transpiled_program": "OPENQASM 3;", "stats": {}, "virtual_physical_mapping": {}},
            "message": "ok",
        }

    fake_module = types.SimpleNamespace(
        submit_job=submit_job,
    )
    monkeypatch.setitem(sys.modules, "sse_driver", fake_module)

    async def _assert(client: _AsyncOqtopusClient) -> None:
        result = await client.run_job(
            OqtopusJobSpec.sampling(device_id="sse", program="OPENQASM 3; qubit[1] q;"),
        )
        assert result.job_id == "job-sse-flat"
        assert result.job_info is not None
        assert result.job_info.result is not None
        assert result.job_info.message == "ok"

    _run_with_async_client(OqtopusConfig(base_url=""), _assert)


def test_run_job_raises_when_sse_driver_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_job_raises_when_sse_driver_missing."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    monkeypatch.delitem(sys.modules, "sse_driver", raising=False)

    async def _assert(client: _AsyncOqtopusClient) -> None:
        with pytest.raises(UserApiError):
            await client.run_job(
                OqtopusJobSpec.sampling(device_id="sse", program="OPENQASM 3;")
            )

    _run_with_async_client(OqtopusConfig(base_url=""), _assert)


def test_sync_wrappers_delegate_to_call() -> None:
    """Test case: test_sync_wrappers_delegate_to_call."""
    client = object.__new__(OqtopusClient)
    called: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_run_async_method(method: Any, *args: Any, **kwargs: Any) -> Any:
        method_name = method.__name__
        called.append((method_name, args, kwargs))
        if method_name == "list_devices":
            return [
                models.DevicesDeviceInfo(
                    device_id="K",
                    device_type="simulator",
                    status="available",
                    n_pending_jobs=0,
                    basis_gates=[],
                    supported_instructions=[],
                    description="sim",
                ),
            ]
        if method_name == "get_device":
            return models.DevicesDeviceInfo(
                device_id="K",
                device_type="simulator",
                status="available",
                n_pending_jobs=0,
                basis_gates=[],
                supported_instructions=[],
                description="sim",
            )
        if method_name == "list_jobs":
            return [
                models.JobsJob(
                    job_id="job-1",
                    name="job",
                    job_type=models.JobsJobType.SAMPLING,
                status=models.JobsJobStatus.SUCCEEDED,
                device_id="K",
                shots=1,
                job_info=models.JobsJobInfo(input="https://example.invalid/job-1/input.zip"),
            ),
        ]
        if method_name == "delete_api_token":
            return None
        if method_name == "submit_job":
            return models.JobsRegisterJobResponse(
                job_id="ok",
                presigned_url=models.JobsJobInfoUploadPresignedURL(
                    url="https://example.invalid/upload",
                    fields=models.JobsJobInfoUploadPresignedURLFields(key="ok/input.zip"),
                ),
            )
        if method_name == "run_job":
            return _job(models.JobsJobType.SAMPLING)
        if method_name == "run_sampling":
            return _job(models.JobsJobType.SAMPLING)
        if method_name == "run_estimation":
            return _job(models.JobsJobType.ESTIMATION)
        if method_name == "run_multi_manual":
            return _job(models.JobsJobType.MULTI_MANUAL)
        if method_name == "run_sse":
            return _job(models.JobsJobType.SSE)
        if method_name == "run_sse_file":
            return _job(models.JobsJobType.SSE)
        if method_name == "get_job":
            return _job(models.JobsJobType.SAMPLING)
        if method_name == "wait_for_job":
            return _job(models.JobsJobType.SAMPLING)
        if method_name == "delete_job":
            return models.SuccessSuccessResponse(message="ok")
        if method_name == "get_job_status":
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.SUCCEEDED)
        if method_name == "cancel_job":
            return models.SuccessSuccessResponse(message="ok")
        if method_name == "get_sselog":
            return JobsGetSselogResponse(file="Zm9v", file_name="x.zip")
        if method_name == "create_api_token":
            return models.ApiTokenApiToken(api_token_secret="secret", api_token_expiration=None)
        if method_name == "get_api_token_status":
            return models.ApiTokenApiTokenStatus(api_token_expiration=None)
        if method_name == "get_announcements_list":
            return models.AnnouncementsGetAnnouncementsListResponse(
                announcements=[
                    models.AnnouncementsGetAnnouncementResponse(
                        id=1,
                        title="t",
                        content="c",
                        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                        end_time=datetime(2025, 12, 31, tzinfo=timezone.utc),
                        publishable=True,
                    ),
                ],
            )
        if method_name == "get_announcement":
            return models.AnnouncementsGetAnnouncementResponse(
                id=1,
                title="t",
                content="c",
                start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2025, 12, 31, tzinfo=timezone.utc),
                publishable=True,
            )
        raise AssertionError(method_name)

    client._run_async_method = fake_run_async_method  # type: ignore[assignment,method-assign]

    assert len(client.list_devices()) == 1
    assert isinstance(client.get_device("d"), OqtopusDevice)
    assert len(client.list_jobs()) == 1
    assert isinstance(client.run_job(OqtopusJobSpec.sampling(device_id="K", program="x")), OqtopusJobResult)
    assert isinstance(client.run_sampling(OqtopusJobSpec.sampling(device_id="K", program="x")), OqtopusSamplingJobResult)
    assert isinstance(
        client.run_estimation(OqtopusJobSpec.estimation(device_id="K", program="x", operator=[{"pauli": "Z0", "coeff": 1}])),
        OqtopusEstimationJobResult,
    )
    assert isinstance(client.run_multi_manual(OqtopusJobSpec.multi_manual(device_id="K", program="x")), OqtopusMultiManualJobResult)
    assert isinstance(client.run_sse(OqtopusJobSpec.sse(device_id="K", program="print('x')")), OqtopusSseJobResult)
    assert isinstance(client.run_sse_file(file_path="a.py", device_id="K"), OqtopusSseJobResult)
    assert client.submit_job(OqtopusJobSpec.sampling(device_id="K", program="x")).job_id == "ok"
    assert isinstance(client.get_job("j"), OqtopusJobResult)
    assert isinstance(client.get_job_result("j"), OqtopusJobResult)
    assert isinstance(client.result("j"), OqtopusJobResult)
    assert isinstance(client.refresh("j"), OqtopusJobResult)
    assert isinstance(client.wait_for_job("j"), OqtopusJobResult)
    assert isinstance(client.wait("j"), OqtopusJobResult)
    assert isinstance(client.delete_job("j"), models.SuccessSuccessResponse)
    assert isinstance(client.get_job_status("j"), models.JobsGetJobStatusResponse)
    assert isinstance(client.status("j"), models.JobsJobStatus)
    assert isinstance(client.is_finished("j"), bool)
    assert isinstance(client.cancel_job("j"), models.SuccessSuccessResponse)
    assert isinstance(client.get_sselog("j"), JobsGetSselogResponse)
    assert isinstance(client.create_api_token(), models.ApiTokenApiToken)
    assert isinstance(client.get_api_token_status(), models.ApiTokenApiTokenStatus)
    assert isinstance(client.get_api_token(), models.ApiTokenApiTokenStatus)
    client.delete_api_token()
    assert isinstance(client.get_announcements_list(), models.AnnouncementsGetAnnouncementsListResponse)
    assert isinstance(client.get_announcement(1), models.AnnouncementsGetAnnouncementResponse)

    methods = {name for name, _, _ in called}
    assert "get_device" in methods
    assert "get_api_token_status" in methods


def test_sync_clients_keep_isolated_configuration() -> None:
    """Test case: test_sync_clients_keep_isolated_configuration."""
    client1 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    client2 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    assert client1 is not client2
    assert client1._config is not client2._config


def test_submit_job_passes_explicit_proxy_to_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_submit_job_passes_explicit_proxy_to_storage."""
    observed: dict[str, object] = {}

    async def _assert(client: _AsyncOqtopusClient) -> None:
        class _JobApi:
            def register_job_id(self, _request_timeout: float | None = None) -> str:
                observed["register_timeout"] = _request_timeout
                return "register"

            def submit_job(
                self,
                job_id: str,
                request: object,
                _request_timeout: float | None = None,
            ) -> str:
                observed["submitted_job_id"] = job_id
                observed["submitted_request"] = request
                observed["submit_timeout"] = _request_timeout
                return "submit"

        async def _fake_call_rest(call: object) -> object:
            if call == "register":
                return models.JobsRegisterJobResponse(
                    job_id="job-1",
                    presigned_url=models.JobsJobInfoUploadPresignedURL(
                        url="https://example.invalid/upload",
                        fields=models.JobsJobInfoUploadPresignedURLFields(
                            key="job-1/input.zip"
                        ),
                    ),
                )
            if call == "submit":
                return models.SuccessSuccessResponse(message="ok")
            raise AssertionError(call)

        async def _fake_upload(
            presigned_url: models.JobsJobInfoUploadPresignedURL,
            data: dict[str, object],
            *,
            timeout_s: int = 60,
            proxy: str | None = None,
        ) -> None:
            observed["upload_url"] = presigned_url.url
            observed["upload_data"] = data
            observed["upload_timeout"] = timeout_s
            observed["upload_proxy"] = proxy

        client._job_api = _JobApi()  # type: ignore[assignment]
        client._call_rest = _fake_call_rest  # type: ignore[assignment,method-assign]
        monkeypatch.setattr("oqtopus_client.services.client.OqtopusStorage.upload", _fake_upload)

        response = await client.submit_job(
            OqtopusJobSpec.sampling(device_id="K", program="OPENQASM 3; qubit[1] q;")
        )

        assert response.job_id == "job-1"

    _run_with_async_client(
        OqtopusConfig(base_url="http://test.local", proxy="http://proxy.local:8080"),
        _assert,
    )

    assert observed["upload_url"] == "https://example.invalid/upload"
    assert observed["upload_proxy"] == "http://proxy.local:8080"


def test_get_sselog_passes_explicit_proxy_to_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_get_sselog_passes_explicit_proxy_to_storage."""
    observed: dict[str, object] = {}

    async def _assert(client: _AsyncOqtopusClient) -> None:
        async def _fake_get_job(job_id: str) -> models.JobsJob:
            observed["job_id"] = job_id
            return models.JobsJob(
                job_id=job_id,
                name="job",
                job_type=models.JobsJobType.SSE,
                status=models.JobsJobStatus.SUCCEEDED,
                device_id="K",
                shots=1,
                    job_info=models.JobsJobInfo(
                        input=models.JobsS3SubmitJobInfo(program=["print('x')"]),
                        sse_log="https://example.invalid/log.zip",
                    ),
            )

        archive_bytes = b"PK\x03\x04dummy-zip"

        async def _fake_download_archive(
            presigned_url: str,
            *,
            timeout_s: int = 60,
            proxy: str | None = None,
        ) -> bytes:
            observed["download_url"] = presigned_url
            observed["download_timeout"] = timeout_s
            observed["download_proxy"] = proxy
            return archive_bytes

        client.get_job = _fake_get_job  # type: ignore[assignment,method-assign]
        monkeypatch.setattr(
            "oqtopus_client.services.client.OqtopusStorage.download_archive",
            _fake_download_archive,
        )

        response = await client.get_sselog("job-1")
        assert response.file_name == "sselog_job-1.log"
        assert base64.b64decode(cast("str", response.file), validate=True) == archive_bytes

    _run_with_async_client(
        OqtopusConfig(base_url="http://test.local", proxy="http://proxy.local:8080"),
        _assert,
    )

    assert observed["download_url"] == "https://example.invalid/log.zip"
    assert observed["download_proxy"] == "http://proxy.local:8080"


def test_get_device_resolves_device_info_with_storage_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_get_device_resolves_device_info_with_storage_proxy."""
    observed: dict[str, object] = {}

    async def _assert(client: _AsyncOqtopusClient) -> None:
        class _DeviceApi:
            def get_device(
                self,
                device_id: str,
                _request_timeout: float | None = None,
            ) -> str:
                observed["device_id"] = device_id
                observed["request_timeout"] = _request_timeout
                return "get-device"

        async def _fake_call_rest(call: object) -> object:
            if call != "get-device":
                raise AssertionError(call)
            return models.DevicesDeviceInfo(
                device_id="K",
                device_type="simulator",
                status="available",
                n_pending_jobs=0,
                basis_gates=[],
                supported_instructions=[],
                description="sim",
                device_info="https://example.invalid/device_info.zip",
            )

        async def _fake_download(
            presigned_url: str,
            *,
            timeout_s: int = 60,
            allow_non_dict: bool = False,
            proxy: str | None = None,
        ) -> dict[str, object]:
            observed["download_url"] = presigned_url
            observed["download_timeout"] = timeout_s
            observed["allow_non_dict"] = allow_non_dict
            observed["download_proxy"] = proxy
            return {"backend": "downloaded"}

        client._device_api = _DeviceApi()  # type: ignore[assignment]
        client._call_rest = _fake_call_rest  # type: ignore[assignment,method-assign]
        monkeypatch.setattr(
            "oqtopus_client.services.client.OqtopusStorage.download",
            _fake_download,
        )

        device = await client.get_device("K")
        assert device.device_info == '{"backend": "downloaded"}'

    _run_with_async_client(
        OqtopusConfig(
            base_url="http://test.local",
            timeout=45.0,
            proxy="http://proxy.local:8080",
        ),
        _assert,
    )

    assert observed["device_id"] == "K"
    assert observed["request_timeout"] == 45.0
    assert observed["download_url"] == "https://example.invalid/device_info.zip"
    assert observed["download_timeout"] == 45
    assert observed["allow_non_dict"] is False
    assert observed["download_proxy"] == "http://proxy.local:8080"


def test_list_devices_resolves_only_presigned_device_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_list_devices_resolves_only_presigned_device_info."""
    observed: dict[str, object] = {}

    async def _assert(client: _AsyncOqtopusClient) -> None:
        class _DeviceApi:
            def list_devices(self, _request_timeout: float | None = None) -> str:
                observed["request_timeout"] = _request_timeout
                return "list-devices"

        async def _fake_call_rest(call: object) -> object:
            if call != "list-devices":
                raise AssertionError(call)
            return [
                models.DevicesDeviceInfo(
                    device_id="plain",
                    device_type="simulator",
                    status="available",
                    n_pending_jobs=0,
                    basis_gates=[],
                    supported_instructions=[],
                    description="sim",
                    device_info='{"backend":"inline"}',
                ),
                models.DevicesDeviceInfo(
                    device_id="remote",
                    device_type="simulator",
                    status="available",
                    n_pending_jobs=0,
                    basis_gates=[],
                    supported_instructions=[],
                    description="sim",
                    device_info="https://example.invalid/device_info.zip",
                ),
            ]

        async def _fake_download(
            presigned_url: str,
            *,
            timeout_s: int = 60,
            allow_non_dict: bool = False,
            proxy: str | None = None,
        ) -> dict[str, object]:
            observed["download"] = (presigned_url, timeout_s, allow_non_dict, proxy)
            return {"backend": "downloaded"}

        client._device_api = _DeviceApi()  # type: ignore[assignment]
        client._call_rest = _fake_call_rest  # type: ignore[assignment,method-assign]
        monkeypatch.setattr(
            "oqtopus_client.services.client.OqtopusStorage.download",
            _fake_download,
        )

        devices = await client.list_devices()
        assert [device.device_info for device in devices] == [
            '{"backend":"inline"}',
            '{"backend": "downloaded"}',
        ]

    _run_with_async_client(OqtopusConfig(base_url="http://test.local"), _assert)

    assert observed["request_timeout"] == 30.0
    assert observed["download"] == (
        "https://example.invalid/device_info.zip",
        30,
        False,
        None,
    )


def test_sync_client_close_does_not_affect_other_clients() -> None:
    """Test case: test_sync_clients_can_coexist_without_shared_state."""
    client1 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    client2 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    assert client1.base_url == client2.base_url == "http://test.local"


def test_sync_client_uses_config_from_file_when_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_sync_client_uses_config_from_file_when_omitted."""
    observed: dict[str, str | Path] = {}

    def _from_file_stub(
        section: str = "default",
        path: str | Path = "~/.config/oqtopus/config.ini",
    ) -> OqtopusConfig:
        observed["section"] = section
        observed["path"] = path
        return OqtopusConfig(base_url="http://test.local")

    monkeypatch.setattr(
        OqtopusConfig,
        "from_file",
        classmethod(lambda cls, section="default", path="~/.config/oqtopus/config.ini": _from_file_stub(section, path)),
    )
    client = OqtopusClient()
    assert client.base_url == "http://test.local"
    assert observed["section"] == "default"
    assert observed["path"] == "~/.config/oqtopus/config.ini"


def test_sync_submit_job_uses_worker_thread_with_active_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_sync_submit_job_uses_worker_thread_with_active_event_loop."""
    observed: dict[str, int] = {}

    async def fake_submit_job(
        self: _AsyncOqtopusClient,
        body: OqtopusJobSpec,
    ) -> models.JobsRegisterJobResponse:
        observed["worker_thread"] = threading.get_ident()
        assert body.device_id == "K"
        return models.JobsRegisterJobResponse(
            job_id="job-42",
            presigned_url=models.JobsJobInfoUploadPresignedURL(
                url="https://example.invalid/upload",
                fields=models.JobsJobInfoUploadPresignedURLFields(
                    key="job-42/input.zip"
                ),
            ),
        )

    monkeypatch.setattr(_AsyncOqtopusClient, "submit_job", fake_submit_job)

    async def _scenario() -> None:
        observed["event_loop_thread"] = threading.get_ident()
        client = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
        response = client.submit_job(OqtopusJobSpec.sampling(device_id="K", program="x"))
        assert response.job_id == "job-42"

    asyncio.run(_scenario())
    assert observed["worker_thread"] != observed["event_loop_thread"]


def test_get_job_requires_valid_job_def_shape() -> None:
    """Test case: test_get_job_requires_valid_job_def_shape."""
    client = object.__new__(OqtopusClient)
    client._run_async_method = lambda method, *args, **kwargs: {"invalid": "shape"}  # type: ignore[assignment,method-assign]

    with pytest.raises(AttributeError):
        client.get_job("job-1")


def test_get_job_resolves_plain_text_combined_program(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test case: test_get_job_resolves_plain_text_combined_program."""

    async def _assert(client: _AsyncOqtopusClient) -> None:
        async def _fake_call_rest(_call: object) -> models.JobsJob:
            return models.JobsJob(
                job_id="job-1",
                name="job",
                job_type=models.JobsJobType.MULTI_MANUAL,
                status=models.JobsJobStatus.SUCCEEDED,
                device_id="K",
                shots=1,
                job_info=models.JobsJobInfo(
                    input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
                    combined_program="https://example.invalid/job-1/combined_program.zip",
                    result=models.JobsS3JobResult(
                        sampling=models.JobsS3SamplingResult(
                            counts={"00": 1},
                            divided_counts={"0": {"0": 1}},
                        )
                    ),
                ),
            )

        async def _fake_download(
            presigned_url: str,
            *,
            timeout_s: int = 60,
            allow_non_dict: bool = False,
            proxy: str | None = None,
        ) -> dict[str, object] | str:
            assert presigned_url == "https://example.invalid/job-1/combined_program.zip"
            assert timeout_s == 60
            assert allow_non_dict is True
            assert proxy == "http://proxy.local:8080"
            return "OPENQASM 3;\nqubit[1] q;\n"

        monkeypatch.setattr(client, "_call_rest", _fake_call_rest)
        monkeypatch.setattr(client, "_job_api", SimpleNamespace(get_job=lambda *_args, **_kwargs: object()))
        monkeypatch.setattr(
            "oqtopus_client.services.client.OqtopusStorage.download",
            _fake_download,
        )

        result = await client.get_job("job-1")
        assert result.job_info is not None
        assert result.job_info.combined_program == "OPENQASM 3;\nqubit[1] q;\n"

    _run_with_async_client(
        OqtopusConfig(base_url="http://test.local", proxy="http://proxy.local:8080"),
        _assert,
    )


def test_run_async_method_delegates_selected_async_method() -> None:
    """Test case: test_run_async_method_delegates_selected_async_method."""
    client = object.__new__(OqtopusClient)
    observed: list[str] = []

    def fake_run_async_method(method: Any, *args: Any, **kwargs: Any) -> Any:
        method_name = method.__name__
        observed.append(method_name)
        if method_name == "submit_job":
            return models.JobsRegisterJobResponse(
                job_id="job-42",
                presigned_url=models.JobsJobInfoUploadPresignedURL(
                    url="https://example.invalid/upload",
                    fields=models.JobsJobInfoUploadPresignedURLFields(
                        key="job-42/input.zip"
                    ),
                ),
            )
        if method_name == "get_job_status":
            return models.JobsGetJobStatusResponse(
                job_id="job-42",
                status=models.JobsJobStatus.RUNNING,
            )
        if method_name == "cancel_job":
            return models.SuccessSuccessResponse(message="ok")
        return []

    client._run_async_method = fake_run_async_method  # type: ignore[assignment,method-assign]

    client.list_devices()
    client.get_api_token()
    submit_response = cast(
        "models.JobsRegisterJobResponse",
        client.submit_job(OqtopusJobSpec.sampling(device_id="K", program="x")),
    )
    status_response = cast(
        "models.JobsGetJobStatusResponse",
        client.get_job_status("job-42"),
    )
    cancel_response = cast(
        "models.SuccessSuccessResponse",
        client.cancel_job("job-42"),
    )

    assert submit_response.job_id == "job-42"
    assert status_response.job_id == "job-42"
    assert cancel_response.message == "ok"
    assert observed == [
        "list_devices",
        "get_api_token_status",
        "submit_job",
        "get_job_status",
        "cancel_job",
    ]
