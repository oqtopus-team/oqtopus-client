from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from oqtopus_client import (
    OqtopusDevice,
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusJobSpec,
    OqtopusJobHandle,
    OqtopusClient,
    OqtopusConfig,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from oqtopus_client.errors import ResponseValidationError, UserApiError


def _build_httpx_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


def test_list_devices_returns_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/devices"
        return httpx.Response(
            200,
            json=[
                {
                    "device_id": "SVSim",
                    "device_type": "simulator",
                    "status": "available",
                    "n_pending_jobs": 0,
                    "basis_gates": ["x", "h"],
                    "supported_instructions": ["measure"],
                    "description": "sim",
                }
            ],
        )

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        res = client.list_devices()
    finally:
        client.close()

    assert len(res) == 1
    assert isinstance(res[0], OqtopusDevice)
    assert res[0].device_id == "SVSim"


def test_submit_job_sends_auth_and_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/jobs"
        assert request.headers["q-api-token"] == "token"
        assert json.loads(request.content)["job_type"] == "sampling"
        return httpx.Response(200, json={"job_id": "job-1"})

    req = OqtopusJobSpec.sampling(
        device_id="Kawasaki",
        shots=100,
        program="OPENQASM 3; qubit[1] q;",
    )

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local", api_token="token"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        res = client.submit_job(req)
    finally:
        client.close()

    assert isinstance(res, OqtopusJobHandle)
    assert res.job_id == "job-1"


def test_submit_job_accepts_job_spec() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/jobs"
        payload = json.loads(request.content)
        assert payload["job_type"] == "sampling"
        assert payload["job_info"]["program"] == ["OPENQASM 3; qubit[1] q;"]
        return httpx.Response(200, json={"job_id": "job-spec"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        res = client.submit_job(OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"))
    finally:
        client.close()

    assert res.job_id == "job-spec"


def test_run_sampling_submits_and_waits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            return httpx.Response(200, json={"job_id": "job-1"})
        if request.method == "GET" and request.url.path == "/jobs/job-1/status":
            return httpx.Response(200, json={"job_id": "job-1", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-1":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "name": "job",
                    "job_type": "sampling",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_sampling(
            OqtopusJobSpec.sampling(device_id="Kawasaki", shots=1, program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-1"


def test_run_sampling_accepts_wrapper_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            assert payload["job_type"] == "sampling"
            assert payload["job_info"]["program"] == ["OPENQASM 3; qubit[1] q;"]
            assert payload["transpiler_info"] == {}
            assert payload["simulator_info"] == {}
            assert payload["mitigation_info"] == {}
            return httpx.Response(200, json={"job_id": "job-1"})
        if request.method == "GET" and request.url.path == "/jobs/job-1/status":
            return httpx.Response(200, json={"job_id": "job-1", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-1":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "name": "job",
                    "job_type": "sampling",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_sampling(
            OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-1"


def test_run_estimation_accepts_wrapper_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            assert payload["job_type"] == "estimation"
            assert payload["job_info"]["operator"] == [{"pauli": "Z0", "coeff": 1}]
            return httpx.Response(200, json={"job_id": "job-2"})
        if request.method == "GET" and request.url.path == "/jobs/job-2/status":
            return httpx.Response(200, json={"job_id": "job-2", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-2":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-2",
                    "name": "job",
                    "job_type": "estimation",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_estimation(
            OqtopusJobSpec.estimation(
                device_id="Kawasaki",
                program="OPENQASM 3; qubit[1] q;",
                operator=[{"pauli": "Z0", "coeff": 1}],
            ),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusEstimationJobResult)
    assert result.job_id == "job-2"


def test_run_multi_manual_accepts_wrapper_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            assert payload["job_type"] == "multi_manual"
            return httpx.Response(200, json={"job_id": "job-mm"})
        if request.method == "GET" and request.url.path == "/jobs/job-mm/status":
            return httpx.Response(200, json={"job_id": "job-mm", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-mm":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-mm",
                    "name": "job",
                    "job_type": "multi_manual",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_multi_manual(
            OqtopusJobSpec.multi_manual(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusMultiManualJobResult)
    assert result.job_id == "job-mm"


def test_run_sse_accepts_wrapper_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            assert payload["job_type"] == "sse"
            assert payload["job_info"]["program"] == [base64.b64encode(b"print('hello')").decode("utf-8")]
            return httpx.Response(200, json={"job_id": "job-sse"})
        if request.method == "GET" and request.url.path == "/jobs/job-sse/status":
            return httpx.Response(200, json={"job_id": "job-sse", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-sse":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-sse",
                    "name": "job",
                    "job_type": "sse",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["print('hello')"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_sse(
            OqtopusJobSpec.sse(device_id="Kawasaki", program="print('hello')"),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusSseJobResult)
    assert result.job_id == "job-sse"


def test_run_sampling_accepts_job_spec_direct_init() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            assert payload["job_type"] == "sampling"
            return httpx.Response(200, json={"job_id": "job-legacy"})
        if request.method == "GET" and request.url.path == "/jobs/job-legacy/status":
            return httpx.Response(200, json={"job_id": "job-legacy", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-legacy":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-legacy",
                    "name": "job",
                    "job_type": "sampling",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.run_sampling(
            OqtopusJobSpec(
                device_id="Kawasaki",
                job_type="sampling",
                program="OPENQASM 3; qubit[1] q;",
            ),
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-legacy"


def test_run_helpers_return_typed_sdk_results(tmp_path: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/jobs":
            payload = json.loads(request.content)
            job_type = payload["job_type"]
            suffix = {
                "sampling": "sampling",
                "estimation": "estimation",
                "multi_manual": "multi",
                "sse": "sse",
            }[job_type]
            return httpx.Response(200, json={"job_id": f"job-{suffix}"})
        if request.method == "GET" and request.url.path.startswith("/jobs/") and request.url.path.endswith("/status"):
            job_id = request.url.path.split("/")[2]
            return httpx.Response(200, json={"job_id": job_id, "status": "succeeded"})
        if request.method == "GET" and request.url.path.startswith("/jobs/"):
            job_id = request.url.path.split("/")[2]
            result: dict[str, Any]
            if job_id == "job-estimation":
                job_type = "estimation"
                result = {"estimation": {"exp_value": 1.0, "stds": 0.1}}
            elif job_id == "job-multi":
                job_type = "multi_manual"
                result = {"sampling": {"counts": {"00": 1}}}
            elif job_id == "job-sse":
                job_type = "sse"
                result = {"sampling": {"counts": {"00": 1}}}
            else:
                job_type = "sampling"
                result = {"sampling": {"counts": {"00": 1}}}
            return httpx.Response(
                200,
                json={
                    "job_id": job_id,
                    "name": "job",
                    "job_type": job_type,
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"], "result": result},
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    script_path = tmp_path / "job.py"
    script_path.write_text("print('hello')\n", encoding="utf-8")

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        base = client.run_job(
            OqtopusJobSpec.sampling(device_id="Kawasaki", shots=1, program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
        sampling = client.run_sampling(
            OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
        estimation = client.run_estimation(
            OqtopusJobSpec.estimation(
                device_id="Kawasaki",
                program="OPENQASM 3; qubit[1] q;",
                operator=[{"pauli": "Z0", "coeff": 1}],
            ),
            interval=0.01,
            timeout=1.0,
        )
        multi = client.run_multi_manual(
            OqtopusJobSpec.multi_manual(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            interval=0.01,
            timeout=1.0,
        )
        sse = client.run_sse(
            OqtopusJobSpec.sse(device_id="Kawasaki", program="print('hello')"),
            interval=0.01,
            timeout=1.0,
        )
        sse_file = client.run_sse_file(
            file_path=script_path,
            device_id="Kawasaki",
            interval=0.01,
            timeout=1.0,
        )
    finally:
        client.close()

    assert isinstance(base, OqtopusJobResult)
    assert isinstance(sampling, OqtopusSamplingJobResult)
    assert isinstance(estimation, OqtopusEstimationJobResult)
    assert isinstance(multi, OqtopusMultiManualJobResult)
    assert isinstance(sse, OqtopusSseJobResult)
    assert isinstance(sse_file, OqtopusSseJobResult)


def test_typed_run_helpers_validate_job_type() -> None:
    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(lambda _: httpx.Response(200))),
    )
    try:
        with pytest.raises(ValueError):
            client.run_sampling(
                OqtopusJobSpec.estimation(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;", operator=[{"pauli": "Z0", "coeff": 1}]),
                timeout=1.0,
            )
        with pytest.raises(ValueError):
            client.run_estimation(OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"), timeout=1.0)
        with pytest.raises(ValueError):
            client.run_multi_manual(OqtopusJobSpec.sse(device_id="Kawasaki", program="print('hello')"), timeout=1.0)
        with pytest.raises(ValueError):
            client.run_sse(OqtopusJobSpec.multi_manual(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"), timeout=1.0)
    finally:
        client.close()


def test_job_request_default_shots_is_1000() -> None:
    req = OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;")
    submit = req.to_submit_job_request()
    assert submit.shots == 1000


def test_job_spec_info_fields_default_to_empty_dict() -> None:
    req = OqtopusJobSpec(device_id="Kawasaki", job_type="sampling", program="OPENQASM 3; qubit[1] q;")
    assert req.transpiler_info == {}
    assert req.simulator_info == {}
    assert req.mitigation_info == {}


def test_list_jobs_serializes_datetime_query() -> None:
    end_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        assert query["end_time"] == end_time.isoformat()
        return httpx.Response(200, json=[])

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        client.list_jobs(end_time=end_time)
    finally:
        client.close()


def test_api_error_raises_user_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "not found"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(UserApiError) as exc_info:
            client.get_job("missing")
    finally:
        client.close()

    assert exc_info.value.status_code == 404
    assert exc_info.value.payload == {"message": "not found"}


def test_get_job_encodes_path_parameter() -> None:
    raw_job_id = "id/with space"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/jobs/id%2Fwith%20space")
        return httpx.Response(
            200,
            json={
                "job_id": "id-1",
                "name": "job",
                "job_type": "sampling",
                "status": "submitted",
                "device_id": "Kawasaki",
                "shots": 1,
                "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
            },
        )

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.get_job(raw_job_id)
    finally:
        client.close()

    assert isinstance(result, OqtopusJobHandle)
    assert result.job_id == "id-1"


def test_wait_for_job_returns_typed_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/jobs/job-1/status":
            return httpx.Response(200, json={"job_id": "job-1", "status": "succeeded"})
        if request.method == "GET" and request.url.path == "/jobs/job-1":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "name": "job",
                    "job_type": "sampling",
                    "status": "succeeded",
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {
                        "program": ["OPENQASM 3; qubit[1] q;"],
                        "result": {"sampling": {"counts": {"00": 1}}},
                    },
                },
            )
        return httpx.Response(404, json={"message": "unexpected path"})

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        result = client.wait_for_job("job-1", interval=0.01, timeout=1.0)
    finally:
        client.close()

    assert isinstance(result, OqtopusSamplingJobResult)


def test_validation_error_raises_response_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "x",
                "title": "t",
                "content": "c",
                "start_time": "2022-10-19T11:45:34+09:00",
                "end_time": "2022-12-19T11:45:34+09:00",
                "publishable": True,
            },
        )

    client = OqtopusClient(
        OqtopusConfig(base_url="http://test.local"),
        client=_build_httpx_client(httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(ResponseValidationError):
            client.get_announcement(1)
    finally:
        client.close()


def test_config_from_env_constructs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OQTOPUS_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("OQTOPUS_API_TOKEN", "secret")
    client = OqtopusClient(OqtopusConfig.from_env())
    try:
        assert isinstance(client, OqtopusClient)
        assert client.base_url == "https://api.example.com"
    finally:
        client.close()


def test_config_argument_is_supported() -> None:
    cfg = OqtopusConfig(
        base_url="https://api.example.com",
        api_token="token",
        timeout=12.5,
        retry_max_attempts=5,
        retry_backoff_seconds=0.7,
        retry_status_codes=frozenset({429, 503}),
        retry_methods=frozenset({"get", "post"}),
    )
    client = OqtopusClient(cfg)
    try:
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 12.5
        assert client.retry_max_attempts == 5
        assert client.retry_backoff_seconds == 0.7
        assert client.retry_status_codes == frozenset({429, 503})
        assert client.retry_methods == frozenset({"GET", "POST"})
    finally:
        client.close()
