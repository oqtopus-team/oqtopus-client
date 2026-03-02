"""Unit tests for oqtopus-client."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

import oqtopus_client.services.client as client_module
from oqtopus_client import (
    OqtopusDevice,
    OqtopusClient,
    OqtopusConfig,
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusJobSpec,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
    UserApiError,
    rest as models,
)
from oqtopus_client.services.client import _AsyncOqtopusClient, _resolve_user_agent


def test_removed_compatibility_module_import_fails() -> None:
    """Test case: test_removed_compatibility_module_import_fails."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("oqtopus_client.client")


def _job(job_type: models.JobsJobType, *, status: models.JobsJobStatus = models.JobsJobStatus.SUCCEEDED) -> models.JobsJobDef:
    result: models.JobsJobResult
    if job_type == models.JobsJobType.ESTIMATION:
        result = models.JobsJobResult(estimation=models.JobsEstimationResult(exp_value=1.0, stds=0.1))
    else:
        result = models.JobsJobResult(sampling=models.JobsSamplingResult(counts={"00": 1}))
    return models.JobsJobDef(
        job_id="job-1",
        name="job",
        job_type=job_type,
        status=status,
        device_id="K",
        shots=1,
        job_info=models.JobsJobInfo(program=["x"], result=result),
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
    client = _AsyncOqtopusClient(OqtopusConfig(base_url=""))
    try:
        assert client.base_url == ""
    finally:
        asyncio.run(client.close())


def test_async_client_sets_headers_and_generated_config() -> None:
    """Test case: test_async_client_sets_headers_and_generated_config."""
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test", api_token="from-config", proxy="http://proxy.local:8080"),
        default_headers={"X-Test": "1"},
    )
    try:
        assert client._headers["q-api-token"] == "from-config"
        assert client._headers["X-Test"] == "1"
        asyncio.run(_initialize_generated_api(client))
        assert client._generated_config is not None
        assert client._generated_config.proxy == "http://proxy.local:8080"
    finally:
        asyncio.run(client.close())


async def _initialize_generated_api(client: _AsyncOqtopusClient) -> None:
    client._initialize_generated_api()


def test_extract_error_message_variants() -> None:
    """Test case: test_extract_error_message_variants."""
    assert _AsyncOqtopusClient._extract_error_message({"message": "m"}) == "m"
    assert _AsyncOqtopusClient._extract_error_message({"error": "e"}) == "e"
    assert _AsyncOqtopusClient._extract_error_message({"error": {"message": "deep"}}) == "deep"
    assert _AsyncOqtopusClient._extract_error_message(" text ") == "text"
    assert _AsyncOqtopusClient._extract_error_message({}) is None


def test_coerce_and_validate_job_type() -> None:
    """Test case: test_coerce_and_validate_job_type."""
    req = _AsyncOqtopusClient._coerce_submit_job_request(
        OqtopusJobSpec.sampling(device_id="K", program="x")
    )
    assert req.job_type == models.JobsJobType.SAMPLING

    _AsyncOqtopusClient._validate_run_job_type(req, models.JobsJobType.SAMPLING)
    with pytest.raises(ValueError):
        _AsyncOqtopusClient._validate_run_job_type(req, models.JobsJobType.ESTIMATION)


def test_wait_for_job_failure_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_wait_for_job_failure_and_timeout."""
    client = _AsyncOqtopusClient(OqtopusConfig(base_url="http://test"))
    try:
        async def status_failed(_: str) -> models.JobsGetJobStatusResponse:
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.FAILED)

        async def status_running(_: str) -> models.JobsGetJobStatusResponse:
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.RUNNING)

        async def get_job(_: str) -> models.JobsJobDef:
            return _job(models.JobsJobType.SAMPLING, status=models.JobsJobStatus.FAILED)

        monkeypatch.setattr(client, "get_job_status", status_failed)
        monkeypatch.setattr(client, "get_job", get_job)
        with pytest.raises(UserApiError):
            asyncio.run(client.wait_for_job("job-1", interval=0.001, timeout=0.01))

        monkeypatch.setattr(client, "get_job_status", status_running)
        with pytest.raises(TimeoutError):
            asyncio.run(client.wait_for_job("job-1", interval=0.001, timeout=0.01))
    finally:
        asyncio.run(client.close())


def test_run_sse_file_forwards_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_sse_file_forwards_kwargs."""
    script = tmp_path / "job.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    observed: dict[str, Any] = {}

    def build_stub(*, file_path: str | Path, device_id: str, **kwargs: Any) -> models.JobsSubmitJobRequest:
        observed["build"] = {"file_path": str(file_path), "device_id": device_id, **kwargs}
        return models.JobsSubmitJobRequest(
            device_id=device_id,
            job_type=models.JobsJobType.SSE,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["encoded"]),
        )

    async def run_sse_stub(self: _AsyncOqtopusClient, job: Any, **kwargs: Any) -> models.JobsJobDef:
        observed["run"] = {"job": job, "kwargs": kwargs}
        return _job(models.JobsJobType.SSE)

    monkeypatch.setattr(_AsyncOqtopusClient, "build_sse_job_request", staticmethod(build_stub))
    monkeypatch.setattr(_AsyncOqtopusClient, "run_sse", run_sse_stub)

    client = _AsyncOqtopusClient(OqtopusConfig(base_url="http://test"))
    try:
        result = asyncio.run(
            client.run_sse_file(
                file_path=script,
                device_id="K",
                name="n",
                description="d",
                timeout=5.0,
                shots=3,
            )
        )
    finally:
        asyncio.run(client.close())

    assert result.job_type == models.JobsJobType.SSE
    assert observed["build"]["device_id"] == "K"
    assert observed["run"]["kwargs"]["timeout"] == 5.0


def test_run_job_uses_sse_sampler_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_job_uses_sse_sampler_in_sse_container."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    fake_module = types.SimpleNamespace(
        req_transpile_and_exec=lambda program, shots, transpiler_info: {
            "job_id": "job-sse-container",
            "name": "job",
            "job_type": "sampling",
            "status": "succeeded",
            "device_id": "sse",
            "shots": shots,
            "job_info": {"program": program, "result": {"sampling": {"counts": {"00": 1}}}},
        }
    )
    monkeypatch.setitem(sys.modules, "sse_sampler", fake_module)

    client = _AsyncOqtopusClient(OqtopusConfig(base_url=""))
    try:
        result = asyncio.run(
            client.run_job(
                OqtopusJobSpec.sampling(device_id="sse", program="OPENQASM 3; qubit[1] q;")
            )
        )
    finally:
        asyncio.run(client.close())

    assert result.job_id == "job-sse-container"


def test_run_job_raises_when_sse_sampler_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_run_job_raises_when_sse_sampler_missing."""
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    monkeypatch.delitem(sys.modules, "sse_sampler", raising=False)

    client = _AsyncOqtopusClient(OqtopusConfig(base_url=""))
    try:
        with pytest.raises(UserApiError):
            asyncio.run(client.run_job(OqtopusJobSpec.sampling(device_id="sse", program="OPENQASM 3;")))
    finally:
        asyncio.run(client.close())


def test_sync_wrappers_delegate_to_call() -> None:
    """Test case: test_sync_wrappers_delegate_to_call."""
    client = object.__new__(OqtopusClient)
    called: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        called.append((name, args, kwargs))
        if name == "list_devices":
            return [
                models.DevicesDeviceInfo(
                    device_id="K",
                    device_type="simulator",
                    status="available",
                    n_pending_jobs=0,
                    basis_gates=[],
                    supported_instructions=[],
                    description="sim",
                )
            ]
        if name == "get_device":
            return models.DevicesDeviceInfo(
                device_id="K",
                device_type="simulator",
                status="available",
                n_pending_jobs=0,
                basis_gates=[],
                supported_instructions=[],
                description="sim",
            )
        if name == "list_jobs":
            return [
                models.JobsGetJobsResponse(
                    job_id="job-1",
                    name="job",
                    job_type=models.JobsJobType.SAMPLING,
                    status=models.JobsJobStatus.SUCCEEDED,
                    device_id="K",
                    shots=1,
                    job_info=models.JobsJobInfo(program=["x"]),
                )
            ]
        if name == "delete_api_token":
            return None
        if name == "submit_job":
            return models.JobsSubmitJobResponse(job_id="ok")
        if name == "run_job":
            return _job(models.JobsJobType.SAMPLING)
        if name == "run_sampling":
            return _job(models.JobsJobType.SAMPLING)
        if name == "run_estimation":
            return _job(models.JobsJobType.ESTIMATION)
        if name == "run_multi_manual":
            return _job(models.JobsJobType.MULTI_MANUAL)
        if name == "run_sse":
            return _job(models.JobsJobType.SSE)
        if name == "run_sse_file":
            return _job(models.JobsJobType.SSE)
        if name == "get_job":
            return _job(models.JobsJobType.SAMPLING)
        if name == "wait_for_job":
            return _job(models.JobsJobType.SAMPLING)
        if name == "delete_job":
            return models.SuccessSuccessResponse(message="ok")
        if name == "get_job_status":
            return models.JobsGetJobStatusResponse(job_id="job-1", status=models.JobsJobStatus.SUCCEEDED)
        if name == "cancel_job":
            return models.SuccessSuccessResponse(message="ok")
        if name == "get_sselog":
            return models.JobsGetSselogResponse(file="Zm9v", file_name="x.zip")
        if name == "create_api_token":
            return models.ApiTokenApiToken(api_token_secret="secret", api_token_expiration=None)
        if name == "get_api_token":
            return models.ApiTokenApiToken(api_token_expiration=None)
        if name == "get_announcements_list":
            return models.AnnouncementsGetAnnouncementsListResponse(
                announcements=[
                    models.AnnouncementsGetAnnouncementResponse(
                        id=1,
                        title="t",
                        content="c",
                        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                        end_time=datetime(2025, 12, 31, tzinfo=timezone.utc),
                        publishable=True,
                    )
                ]
            )
        if name == "get_announcement":
            return models.AnnouncementsGetAnnouncementResponse(
                id=1,
                title="t",
                content="c",
                start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2025, 12, 31, tzinfo=timezone.utc),
                publishable=True,
            )
        raise AssertionError(name)

    client._call = fake_call  # type: ignore[assignment,method-assign]
    client._async = Mock()
    client._runtime = Mock()
    client._closed = False

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
    assert isinstance(client.get_sselog("j"), models.JobsGetSselogResponse)
    assert isinstance(client.create_api_token(), models.ApiTokenApiToken)
    assert isinstance(client.get_api_token(), models.ApiTokenApiToken)
    client.delete_api_token()
    assert isinstance(client.get_announcements_list(), models.AnnouncementsGetAnnouncementsListResponse)
    assert isinstance(client.get_announcement(1), models.AnnouncementsGetAnnouncementResponse)

    methods = {name for name, _, _ in called}
    assert "get_device" in methods
    assert "get_api_token" in methods


def test_sync_client_close_is_idempotent_and_blocks_calls() -> None:
    """Test case: test_sync_client_close_is_idempotent_and_blocks_calls."""
    client = object.__new__(OqtopusClient)
    client._closed = False
    client._runtime = Mock()
    client._async = Mock()
    client._finalizer = Mock(alive=True)

    client.close()
    client.close()
    with pytest.raises(RuntimeError):
        client.list_devices()


def test_sync_clients_share_runtime() -> None:
    """Test case: test_sync_clients_share_runtime."""
    client_module._shutdown_shared_runtime()
    client1 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    client2 = OqtopusClient(OqtopusConfig(base_url="http://test.local"))
    try:
        assert client1._runtime is client2._runtime
    finally:
        client1.close()
        client2.close()
        client_module._shutdown_shared_runtime()


def test_sync_client_uses_config_from_file_when_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_sync_client_uses_config_from_file_when_omitted."""
    client_module._shutdown_shared_runtime()
    observed: dict[str, str | Path] = {}

    def _from_file_stub(
        section: str = "default",
        path: str | Path = "~/.config/oqtopus/config.ini",
    ) -> OqtopusConfig:
        observed["section"] = section
        observed["path"] = path
        return OqtopusConfig(base_url="http://test.local")

    monkeypatch.setattr(
        client_module.OqtopusConfig,
        "from_file",
        classmethod(lambda cls, section="default", path="~/.config/oqtopus/config.ini": _from_file_stub(section, path)),
    )
    client = OqtopusClient()
    try:
        assert client.base_url == "http://test.local"
        assert observed["section"] == "default"
        assert observed["path"] == "~/.config/oqtopus/config.ini"
    finally:
        client.close()
        client_module._shutdown_shared_runtime()


def test_get_job_requires_valid_job_def_shape() -> None:
    """Test case: test_get_job_requires_valid_job_def_shape."""
    client = object.__new__(OqtopusClient)
    client._async = Mock()
    client._runtime = Mock()
    client._closed = False
    client._call = lambda name, *args, **kwargs: {"invalid": "shape"}  # type: ignore[assignment,method-assign]

    with pytest.raises(AttributeError):
        client.get_job("job-1")
