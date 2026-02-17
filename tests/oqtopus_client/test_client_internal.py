from __future__ import annotations

import asyncio
import json
import sys
import types
from datetime import datetime, timezone
from enum import Enum
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from pydantic import BaseModel

from oqtopus_client import (
    OqtopusDevice,
    OqtopusClient,
    OqtopusConfig,
    OqtopusEstimationJobResult,
    OqtopusJobHandle,
    OqtopusJobResult,
    OqtopusJobSpec,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
    models,
)
from oqtopus_client.client import _AsyncOqtopusClient, _resolve_user_agent
from oqtopus_client.errors import ResponseValidationError, UserApiError


def _async_client(handler: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


class _DummyBody(BaseModel):
    key: str
    optional: str | None = None


def test_resolve_user_agent_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    # simulate PackageNotFoundError path by raising that exact type
    monkeypatch.setattr(
        "oqtopus_client.client.version",
        lambda _: (_ for _ in ()).throw(PackageNotFoundError()),
    )
    assert _resolve_user_agent().startswith("oqtopus-client/")
    assert _resolve_user_agent().endswith("unknown")


def test_async_client_constructor_validation_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url=""))
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url="http://test", retry_max_attempts=0))
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(OqtopusConfig(base_url="http://test", retry_backoff_seconds=-1))
    with pytest.raises(ValueError):
        _AsyncOqtopusClient(
            OqtopusConfig(base_url="http://test", api_token="x", api_token_file=tmp_path / "token.txt")
        )


def test_async_client_allows_empty_base_url_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url=""),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        assert client.base_url == ""
    finally:
        asyncio.run(client.close())


def test_async_client_accepts_default_headers_and_token_file(tmp_path: Path) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("from-file", encoding="utf-8")
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test", api_token_file=token_file),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json=[]))),
        default_headers={"X-Test": "1"},
    )
    try:
        assert client._headers["q-api-token"] == "from-file"
        assert client._headers["X-Test"] == "1"
    finally:
        asyncio.run(client.close())


def test_load_api_token_from_file_formats(tmp_path: Path) -> None:
    plain = tmp_path / "plain.txt"
    plain.write_text("plain-token\n", encoding="utf-8")
    assert _AsyncOqtopusClient._load_api_token_from_file(plain) == "plain-token"

    json_str = tmp_path / "json_string.txt"
    json_str.write_text(json.dumps("string-token"), encoding="utf-8")
    assert _AsyncOqtopusClient._load_api_token_from_file(json_str) == "string-token"

    json_map = tmp_path / "json_map.txt"
    json_map.write_text(json.dumps({"api_token_secret": "map-token"}), encoding="utf-8")
    assert _AsyncOqtopusClient._load_api_token_from_file(json_map) == "map-token"

    empty = tmp_path / "empty.txt"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _AsyncOqtopusClient._load_api_token_from_file(empty)

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"invalid": "value"}), encoding="utf-8")
    with pytest.raises(ValueError):
        _AsyncOqtopusClient._load_api_token_from_file(bad)


def test_helper_methods_cover_value_serialization_and_error_parsing() -> None:
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        class _E(Enum):
            A = "a"

        assert client._serialize_value(None) is None
        assert client._serialize_value(datetime(2025, 1, 1, tzinfo=timezone.utc)).startswith("2025-01-01")
        assert client._serialize_value(_E.A) == "a"
        assert client._serialize_value([_E.A, datetime(2025, 1, 1, tzinfo=timezone.utc)]) == [
            "a",
            "2025-01-01T00:00:00+00:00",
        ]
        assert client._json_body(_DummyBody(key="v")) == {"key": "v"}
        assert client._json_body({"x": 1}) == {"x": 1}
        assert client._path_param("a b/c") == "a%20b%2Fc"
        assert client._job_type_of({"job_type": models.JobsJobType.SSE}) == "sse"
        assert client._job_type_of({"job_type": "sampling"}) == "sampling"
        assert client._job_type_of({"job_type": 1}) is None
        model_job = models.JobsSubmitJobRequest(
            device_id="K",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["x"]),
        )
        assert client._job_type_of(model_job) == "sampling"
        assert client._serialize_value("raw") == "raw"
        assert client._extract_error_message({"message": "m"}) == "m"
        assert client._extract_error_message({"error": "e"}) == "e"
        assert client._extract_error_message({"error": {"message": "deep"}}) == "deep"
        assert client._extract_error_message("  text ") == "text"
        assert client._extract_error_message({}) is None
        assert client._should_retry_network_error("GET", 1) is True
        assert client._should_retry_network_error("POST", 1) is False
        assert client._should_retry_response("GET", 500, 1) is True
        assert client._should_retry_response("POST", 500, 1) is False
    finally:
        asyncio.run(client.close())


def test_safe_json_handles_empty_and_non_json() -> None:
    empty = httpx.Response(200, content=b"")
    plain = httpx.Response(200, content=b"plain")
    assert _AsyncOqtopusClient._safe_json(empty) is None
    assert _AsyncOqtopusClient._safe_json(plain) == "plain"


def test_request_retries_network_error_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"job_id": "job-1"})

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0, retry_methods=frozenset({"POST"})),
        client=_async_client(httpx.MockTransport(handler)),
    )
    try:
        result = asyncio.run(client.submit_job({"device_id": "K", "job_type": "sampling", "job_info": {"program": ["x"]}}))
    finally:
        asyncio.run(client.close())
    assert result.job_id == "job-1"
    assert calls["n"] == 2


def test_request_network_error_raises_user_api_error_without_retry() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0),
        client=_async_client(httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(UserApiError):
            asyncio.run(client.submit_job({"device_id": "K", "job_type": "sampling", "job_info": {"program": ["x"]}}))
    finally:
        asyncio.run(client.close())


def test_request_covers_response_none_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_max_attempts=1),
        client=_async_client(httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(client, "_should_retry_network_error", lambda method, attempt: True)
    try:
        with pytest.raises(UserApiError):
            asyncio.run(client._request("GET", "/jobs"))
    finally:
        asyncio.run(client.close())


def test_request_retries_server_error_and_parse_none_path() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="retry")
        return httpx.Response(204, content=b"")

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0),
        client=_async_client(httpx.MockTransport(handler)),
    )
    try:
        assert asyncio.run(client.delete_api_token()) is None
    finally:
        asyncio.run(client.close())
    assert calls["n"] == 2


def test_sleep_before_retry_respects_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    waited: list[float] = []

    async def _fake_sleep(value: float) -> None:
        waited.append(value)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0.25),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    monkeypatch.setattr("oqtopus_client.client.asyncio.sleep", _fake_sleep)
    try:
        asyncio.run(client._sleep_before_retry(2))
    finally:
        asyncio.run(client.close())
    assert waited == [0.5]


def test_request_raises_response_validation_error() -> None:
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={"invalid": "shape"}))),
    )
    try:
        with pytest.raises(ResponseValidationError):
            asyncio.run(client.get_device("K"))
    finally:
        asyncio.run(client.close())


def test_wait_for_job_failure_and_timeout_and_validation() -> None:
    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        with pytest.raises(ValueError):
            asyncio.run(client.wait_for_job("j", interval=0))
        with pytest.raises(ValueError):
            asyncio.run(client.wait_for_job("j", interval_backoff=0.9))
        with pytest.raises(ValueError):
            asyncio.run(client.wait_for_job("j", max_interval=0))
        with pytest.raises(ValueError):
            asyncio.run(client.wait_for_job("j", timeout=0))
    finally:
        asyncio.run(client.close())

    calls = {"n": 0}

    def handler_failed(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            return httpx.Response(200, json={"job_id": "job-1", "status": "failed"})
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "name": "job",
                "job_type": "sampling",
                "status": "failed",
                "device_id": "K",
                "shots": 1,
                "job_info": {"program": ["x"]},
            },
        )

    client_failed = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(handler_failed)),
    )
    try:
        with pytest.raises(UserApiError):
            asyncio.run(client_failed.wait_for_job("job-1", interval=0.001, timeout=0.01))
    finally:
        asyncio.run(client_failed.close())

    def handler_running(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            calls["n"] += 1
            return httpx.Response(200, json={"job_id": "job-1", "status": "running"})
        return httpx.Response(404, json={"message": "unexpected"})

    client_timeout = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0),
        client=_async_client(httpx.MockTransport(handler_running)),
    )
    try:
        with pytest.raises(TimeoutError):
            asyncio.run(client_timeout.wait_for_job("job-1", interval=0.001, timeout=0.002))
    finally:
        asyncio.run(client_timeout.close())
    assert calls["n"] >= 1


def test_wait_for_job_covers_remaining_timeout_and_max_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    sequence = iter(
        [
            models.JobsJobStatus.RUNNING,
            models.JobsJobStatus.RUNNING,
            models.JobsJobStatus.SUCCEEDED,
        ]
    )
    sleep_values: list[float] = []

    async def _fake_sleep(value: float) -> None:
        sleep_values.append(value)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            status = next(sequence)
            return httpx.Response(200, json={"job_id": "job-1", "status": status.value})
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "name": "job",
                "job_type": "sampling",
                "status": "succeeded",
                "device_id": "K",
                "shots": 1,
                "job_info": {"program": ["x"]},
            },
        )

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(handler)),
    )
    monkeypatch.setattr("oqtopus_client.client.asyncio.sleep", _fake_sleep)
    try:
        job = asyncio.run(
            client.wait_for_job(
                "job-1",
                interval=0.01,
                interval_backoff=2.0,
                max_interval=0.015,
                timeout=1.0,
            )
        )
        assert job.job_id == "job-1"
    finally:
        asyncio.run(client.close())
    assert sleep_values[0] == 0.01
    assert sleep_values[1] == 0.015

    monotonic_values = iter([100.0, 100.0, 100.2])
    monkeypatch.setattr("oqtopus_client.client.monotonic", lambda: next(monotonic_values))

    def running_only(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            return httpx.Response(200, json={"job_id": "job-1", "status": "running"})
        return httpx.Response(404, json={"message": "unexpected"})

    client_timeout = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(running_only)),
    )
    try:
        with pytest.raises(TimeoutError):
            asyncio.run(client_timeout.wait_for_job("job-1", interval=0.01, timeout=0.1))
    finally:
        asyncio.run(client_timeout.close())


def test_run_sse_file_forwards_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        return models.JobsJobDef(
            job_id="job-1",
            name="job",
            job_type=models.JobsJobType.SSE,
            status=models.JobsJobStatus.SUCCEEDED,
            device_id="K",
            shots=1,
            job_info=models.JobsJobInfo(program=["x"]),
        )

    monkeypatch.setattr(_AsyncOqtopusClient, "build_sse_job_request", staticmethod(build_stub))
    monkeypatch.setattr(_AsyncOqtopusClient, "run_sse", run_sse_stub)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        job = asyncio.run(
            client.run_sse_file(
                file_path=script,
                device_id="K",
                name="n",
                description="d",
                max_encoded_file_size=1024,
                timeout=10,
            )
        )
    finally:
        asyncio.run(client.close())

    assert job.job_id == "job-1"
    assert observed["build"]["name"] == "n"
    assert observed["run"]["kwargs"]["timeout"] == 10


def test_run_job_uses_sse_sampler_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")

    def _never_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP transport must not be used in sse_container mode")

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

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url=""),
        client=_async_client(httpx.MockTransport(_never_called)),
    )
    try:
        req = models.JobsSubmitJobRequest(
            device_id="sse",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q; bit[1] c; c = measure q;"]),
        )
        result = asyncio.run(client.run_job(req))
    finally:
        asyncio.run(client.close())

    assert result.job_id == "job-sse-container"
    assert result.status == models.JobsJobStatus.SUCCEEDED


def test_run_job_accepts_legacy_dict_response_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")

    class LegacyModel:
        def _payload(self) -> dict[str, Any]:
            return {
                "job_id": "job-sse-legacy",
                "name": "job",
                "job_type": "sampling",
                "status": "succeeded",
                "device_id": "sse",
                "shots": 1,
                "job_info": {"program": ["OPENQASM 3;"], "result": {"sampling": {"counts": {"00": 1}}}},
            }

        def json(self) -> str:
            return json.dumps(self._payload())

    fake_module = types.SimpleNamespace(
        req_transpile_and_exec=lambda program, shots, transpiler_info: LegacyModel()
    )
    monkeypatch.setitem(sys.modules, "sse_sampler", fake_module)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url=""),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        req = models.JobsSubmitJobRequest(
            device_id="sse",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3;"]),
        )
        result = asyncio.run(client.run_job(req))
    finally:
        asyncio.run(client.close())

    assert result.job_id == "job-sse-legacy"
    assert result.status == models.JobsJobStatus.SUCCEEDED


def test_run_job_raises_when_sse_sampler_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")
    monkeypatch.delitem(sys.modules, "sse_sampler", raising=False)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url=""),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        req = models.JobsSubmitJobRequest(
            device_id="sse",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["x"]),
        )
        with pytest.raises(UserApiError):
            asyncio.run(client.run_job(req))
    finally:
        asyncio.run(client.close())


def test_run_job_accepts_attribute_based_response_in_sse_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_ENV", "sse_container")

    class ForeignJobInfo:
        def __init__(self) -> None:
            self.program = ["OPENQASM 3;"]
            self.result = {"sampling": {"counts": {"00": 1}}}

    class ForeignJobDef:
        def __init__(self) -> None:
            self.job_id = "job-sse-attrs"
            self.name = "job"
            self.description = None
            self.job_type = "sampling"
            self.status = "succeeded"
            self.device_id = "sse"
            self.shots = 1
            self.job_info = ForeignJobInfo()
            self.transpiler_info = {}
            self.simulator_info = {}
            self.mitigation_info = {}

    fake_module = types.SimpleNamespace(
        req_transpile_and_exec=lambda program, shots, transpiler_info: ForeignJobDef()
    )
    monkeypatch.setitem(sys.modules, "sse_sampler", fake_module)

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url=""),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    try:
        req = models.JobsSubmitJobRequest(
            device_id="sse",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3;"]),
        )
        result = asyncio.run(client.run_job(req))
    finally:
        asyncio.run(client.close())

    assert result.job_id == "job-sse-attrs"
    assert result.status == models.JobsJobStatus.SUCCEEDED


def test_build_sse_job_request_validates_file_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    with pytest.raises(ValueError):
        _AsyncOqtopusClient.build_sse_job_request(missing, device_id="K")

    not_file = tmp_path / "dir"
    not_file.mkdir()
    with pytest.raises(ValueError):
        _AsyncOqtopusClient.build_sse_job_request(not_file, device_id="K")

    not_python = tmp_path / "job.txt"
    not_python.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        _AsyncOqtopusClient.build_sse_job_request(not_python, device_id="K")

    py_file = tmp_path / "job.py"
    py_file.write_bytes(b"x" * 4)
    with pytest.raises(ValueError):
        _AsyncOqtopusClient.build_sse_job_request(py_file, device_id="K", max_encoded_file_size=1)


def test_async_run_helpers_and_endpoint_wrappers() -> None:
    statuses = {"job-1": "succeeded"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json={"job_id": body.get("name", "job-1")})
        if request.method == "GET" and request.url.path.endswith("/sselog"):
            return httpx.Response(200, json={"file_name": "x.zip", "file": "eA=="})
        if request.method == "GET" and request.url.path.endswith("/status"):
            job_id = request.url.path.split("/")[-2]
            return httpx.Response(200, json={"job_id": job_id, "status": statuses[job_id]})
        if request.method == "GET" and request.url.path.startswith("/jobs/") and not request.url.path.endswith("/status"):
            job_id = request.url.path.split("/")[-1]
            return httpx.Response(
                200,
                json={
                    "job_id": job_id,
                    "name": job_id,
                    "job_type": "sampling",
                    "status": statuses[job_id],
                    "device_id": "K",
                    "shots": 1,
                    "job_info": {"program": ["x"]},
                },
            )
        if request.method == "DELETE" and request.url.path.startswith("/jobs/"):
            return httpx.Response(200, json={"message": "ok"})
        if request.method == "POST" and request.url.path.endswith("/cancel"):
            return httpx.Response(200, json={"message": "ok"})
        if request.method == "POST" and request.url.path == "/api-token":
            return httpx.Response(200, json=[{"api_token_secret": "s"}])
        if request.method == "GET" and request.url.path == "/api-token":
            return httpx.Response(200, json=[{"api_token_secret": "s"}])
        if request.method == "GET" and request.url.path == "/announcements":
            return httpx.Response(200, json={"announcements": []})
        if request.method == "GET" and request.url.path.startswith("/announcements/"):
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "title": "t",
                    "content": "c",
                    "start_time": "2025-01-01T00:00:00+00:00",
                    "end_time": "2025-01-02T00:00:00+00:00",
                    "publishable": True,
                },
            )
        if request.method == "GET" and request.url.path.startswith("/devices/"):
            return httpx.Response(
                200,
                json={
                    "device_id": "K",
                    "device_type": "simulator",
                    "status": "available",
                    "n_pending_jobs": 0,
                    "basis_gates": ["x"],
                    "supported_instructions": ["measure"],
                    "description": "device",
                },
            )
        return httpx.Response(200, json=[])

    client = _AsyncOqtopusClient(
        OqtopusConfig(base_url="http://test.local", retry_backoff_seconds=0),
        client=_async_client(httpx.MockTransport(handler)),
    )
    try:
        req_sampling = models.JobsSubmitJobRequest(
            name="job-1",
            device_id="K",
            job_type=models.JobsJobType.SAMPLING,
            shots=1,
            job_info=models.JobsSubmitJobInfo(program=["x"]),
        )
        req_estimation = req_sampling.model_copy(update={"name": "job-1", "job_type": models.JobsJobType.ESTIMATION})
        req_multi = req_sampling.model_copy(update={"name": "job-1", "job_type": models.JobsJobType.MULTI_MANUAL})
        req_sse = req_sampling.model_copy(update={"name": "job-1", "job_type": models.JobsJobType.SSE})

        assert asyncio.run(client.run_estimation(req_estimation, interval=0.001, timeout=0.01)).job_id == "job-1"
        assert asyncio.run(client.run_multi_manual(req_multi, interval=0.001, timeout=0.01)).job_id == "job-1"
        assert asyncio.run(client.run_sse(req_sse, interval=0.001, timeout=0.01)).job_id == "job-1"

        seen: list[str] = []
        job = asyncio.run(client.wait_for_job("job-1", interval=0.001, timeout=0.01, on_status=lambda s: seen.append(s.status.value)))
        assert job.job_id == "job-1"
        assert seen

        assert asyncio.run(client.delete_job("job-1")).message == "ok"
        assert asyncio.run(client.cancel_job("job-1")).message == "ok"
        assert asyncio.run(client.get_sselog("job-1")).file_name == "x.zip"
        assert asyncio.run(client.create_api_token()).api_token_secret == "s"
        assert asyncio.run(client.get_api_token())[0].api_token_secret == "s"
        assert asyncio.run(client.get_announcements_list()).announcements == []
        assert asyncio.run(client.get_announcement(1)).id == 1
        assert asyncio.run(client.get_device("K")).device_id == "K"
    finally:
        asyncio.run(client.close())


def test_config_with_api_token_file_constructor(tmp_path: Path) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("secret", encoding="utf-8")
    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local", api_token_file=token_file),
        client=_async_client(httpx.MockTransport(lambda request: httpx.Response(200, json=[]))),
    )
    try:
        assert client.base_url == "http://test.local"
    finally:
        client.close()


def test_sync_wrappers_delegate_to_call(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object.__new__(OqtopusClient)
    called: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _job(job_type: models.JobsJobType) -> models.JobsJobDef:
        result: models.JobsJobResult
        if job_type == models.JobsJobType.ESTIMATION:
            result = models.JobsJobResult(estimation=models.JobsEstimationResult(exp_value=1.0, stds=0.1))
        else:
            result = models.JobsJobResult(sampling=models.JobsSamplingResult(counts={"00": 1}))
        return models.JobsJobDef(
            job_id="job-1",
            name="job",
            job_type=job_type,
            status=models.JobsJobStatus.SUCCEEDED,
            device_id="K",
            shots=1,
            job_info=models.JobsJobInfo(program=["x"], result=result),
        )

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
            return [models.ApiTokenApiToken(api_token_expiration=None)]
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
        return "ok"

    client._call = fake_call  # type: ignore[assignment,method-assign]
    client._async = Mock()
    client._runtime = Mock()

    assert len(client.list_devices()) == 1
    assert isinstance(client.get_device("d"), OqtopusDevice)
    listed_jobs = client.list_jobs()
    assert len(listed_jobs) == 1
    assert isinstance(listed_jobs[0], OqtopusJobHandle)
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
    assert isinstance(client.get_job("j"), OqtopusJobHandle)
    assert isinstance(client.get_job_result("j"), OqtopusJobResult)
    assert isinstance(client.wait_for_job("j"), OqtopusJobResult)
    assert isinstance(client.delete_job("j"), models.SuccessSuccessResponse)
    assert isinstance(client.get_job_status("j"), models.JobsGetJobStatusResponse)
    assert isinstance(client.cancel_job("j"), models.SuccessSuccessResponse)
    assert isinstance(client.get_sselog("j"), models.JobsGetSselogResponse)
    assert isinstance(client.create_api_token(), models.ApiTokenApiToken)
    assert isinstance(client.get_api_token(), list)
    client.delete_api_token()
    assert isinstance(client.get_announcements_list(), models.AnnouncementsGetAnnouncementsListResponse)
    assert isinstance(client.get_announcement(1), models.AnnouncementsGetAnnouncementResponse)
    client.set_api_token("token")

    methods = {name for name, _, _ in called}
    assert "get_device" in methods
    assert "get_api_token" in methods
    client._async.set_api_token.assert_called_once_with("token")
