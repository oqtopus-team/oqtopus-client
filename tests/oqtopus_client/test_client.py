"""Unit tests for oqtopus-client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
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


def _job(job_type: models.JobsJobType, *, status: models.JobsJobStatus = models.JobsJobStatus.SUCCEEDED) -> models.JobsJobDef:
    result: models.JobsJobResult
    if job_type == models.JobsJobType.ESTIMATION:
        result = models.JobsJobResult(estimation=models.JobsEstimationResult(exp_value=1.0, stds=0.1))
    else:
        result = models.JobsJobResult(sampling=models.JobsSamplingResult(counts={"00": 1}))
    submitted_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    ready_at = datetime(2025, 1, 2, 3, 4, 6, tzinfo=timezone.utc)
    running_at = datetime(2025, 1, 2, 3, 4, 7, tzinfo=timezone.utc)
    ended_at = datetime(2025, 1, 2, 3, 4, 8, tzinfo=timezone.utc)
    return models.JobsJobDef(
        job_id="job-1",
        name="job",
        description="test job",
        job_type=job_type,
        status=status,
        device_id="K",
        shots=1,
        transpiler_info={"backend": "oqtopus"},
        simulator_info={"seed": 7},
        mitigation_info={"enabled": True},
        job_info=models.JobsJobInfo(
            program=["OPENQASM 3; qubit[1] q;"],
            result=result,
            transpile_result=models.JobsTranspileResult(
                transpiled_program="OPENQASM 3; // transpiled",
                stats={},
                virtual_physical_mapping={"qubit_mapping": {"0": 0}},
            ),
            message="queued",
        ),
        execution_time=1.23,
        submitted_at=submitted_at,
        ready_at=ready_at,
        running_at=running_at,
        ended_at=ended_at,
    )


def _build_client_with_fake_call(fake_call: Any) -> OqtopusClient:
    client = object.__new__(OqtopusClient)
    client._call = fake_call  # type: ignore[assignment,method-assign]
    client._async = Mock()
    client._runtime = Mock()
    client._closed = False
    return client


def test_submit_job_accepts_job_spec() -> None:
    """Test case: test_submit_job_accepts_job_spec."""
    called: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_call(method_name: str, *args: Any, **kwargs: Any) -> Any:
        called.append((method_name, args, kwargs))
        return models.JobsSubmitJobResponse(job_id="job-1")

    client = _build_client_with_fake_call(fake_call)
    res = client.submit_job(OqtopusJobSpec.sampling(device_id="K", program="OPENQASM 3; qubit[1] q;"))

    assert res.job_id == "job-1"
    assert called[0][0] == "submit_job"


def test_get_job_returns_extended_job_result() -> None:
    """Test case: test_get_job_returns_extended_job_result."""
    client = _build_client_with_fake_call(lambda method_name, *args, **kwargs: _job(models.JobsJobType.SAMPLING))

    result = client.get_job("job-1")

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-1"
    assert result.status == models.JobsJobStatus.SUCCEEDED
    assert result.name == "job"
    assert result.description == "test job"
    assert result.device_id == "K"
    assert result.shots == 1
    assert result.execution_time == 1.23
    assert result.transpiler_info == {"backend": "oqtopus"}
    assert result.simulator_info == {"seed": 7}
    assert result.mitigation_info == {"enabled": True}
    assert result.submitted_at == datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert result.ready_at == datetime(2025, 1, 2, 3, 4, 6, tzinfo=timezone.utc)
    assert result.running_at == datetime(2025, 1, 2, 3, 4, 7, tzinfo=timezone.utc)
    assert result.ended_at == datetime(2025, 1, 2, 3, 4, 8, tzinfo=timezone.utc)
    assert result.message == "queued"
    assert isinstance(result.transpile_result, models.JobsTranspileResult)


def test_result_aliases_return_job_result() -> None:
    """Test case: test_result_aliases_return_job_result."""
    client = _build_client_with_fake_call(lambda method_name, *args, **kwargs: _job(models.JobsJobType.SAMPLING))

    assert isinstance(client.get_job_result("job-1"), OqtopusJobResult)
    assert isinstance(client.result("job-1"), OqtopusJobResult)
    assert isinstance(client.refresh("job-1"), OqtopusJobResult)


def test_run_helpers_return_typed_results() -> None:
    """Test case: test_run_helpers_return_typed_results."""
    def fake_call(method_name: str, *args: Any, **kwargs: Any) -> Any:
        mapping = {
            "run_job": models.JobsJobType.SAMPLING,
            "run_sampling": models.JobsJobType.SAMPLING,
            "run_estimation": models.JobsJobType.ESTIMATION,
            "run_multi_manual": models.JobsJobType.MULTI_MANUAL,
            "run_sse": models.JobsJobType.SSE,
            "run_sse_file": models.JobsJobType.SSE,
        }
        return _job(mapping[method_name])

    client = _build_client_with_fake_call(fake_call)

    assert isinstance(client.run_job(OqtopusJobSpec.sampling(device_id="K", program="x")), OqtopusJobResult)
    sampling_result = client.run_sampling(
        OqtopusJobSpec.sampling(device_id="K", program="x"),
    )
    assert isinstance(sampling_result, OqtopusSamplingJobResult)
    assert sampling_result.submitted_at == datetime(
        2025,
        1,
        2,
        3,
        4,
        5,
        tzinfo=timezone.utc,
    )
    assert isinstance(
        client.run_estimation(OqtopusJobSpec.estimation(device_id="K", program="x", operator=[{"pauli": "Z0", "coeff": 1}])),
        OqtopusEstimationJobResult,
    )
    assert isinstance(client.run_multi_manual(OqtopusJobSpec.multi_manual(device_id="K", program="x")), OqtopusMultiManualJobResult)
    assert isinstance(client.run_sse(OqtopusJobSpec.sse(device_id="K", program="print('x')")), OqtopusSseJobResult)


def test_wait_for_job_returns_failed_result() -> None:
    """Test case: test_wait_for_job_returns_failed_result."""

    def fake_call(method_name: str, *args: Any, **kwargs: Any) -> Any:
        assert method_name == "wait_for_job"
        return _job(models.JobsJobType.SAMPLING, status=models.JobsJobStatus.FAILED)

    client = _build_client_with_fake_call(fake_call)

    result = client.wait_for_job("job-1")

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.status == models.JobsJobStatus.FAILED


def test_list_jobs_and_filters_passthrough() -> None:
    """Test case: test_list_jobs_and_filters_passthrough."""
    now = datetime.now(timezone.utc)

    def fake_call(method_name: str, *args: Any, **kwargs: Any) -> Any:
        assert method_name == "list_jobs"
        assert kwargs["end_time"] == now
        return [
            models.JobsGetJobsResponse(
                job_id="job-1",
                name="job",
                job_type=models.JobsJobType.SAMPLING,
                status=models.JobsJobStatus.SUCCEEDED,
                device_id="K",
                shots=1,
                job_info=models.JobsJobInfo(program=["x"]),
            ),
        ]

    client = _build_client_with_fake_call(fake_call)
    jobs = client.list_jobs(end_time=now)
    assert len(jobs) == 1


def test_status_and_cancel_helpers() -> None:
    """Test case: test_status_and_cancel_helpers."""
    def fake_call(method_name: str, *args: Any, **kwargs: Any) -> Any:
        if method_name == "get_job_status":
            return models.JobsGetJobStatusResponse(job_id=args[0], status=models.JobsJobStatus.SUCCEEDED)
        if method_name == "cancel_job":
            return models.SuccessSuccessResponse(message="ok")
        raise AssertionError(method_name)

    client = _build_client_with_fake_call(fake_call)

    assert client.status("job-1") == models.JobsJobStatus.SUCCEEDED
    assert client.is_finished("job-1") is True
    assert client.cancel_job("job-1").message == "ok"


def test_api_error_propagates() -> None:
    """Test case: test_api_error_propagates."""
    client = _build_client_with_fake_call(lambda method_name, *args, **kwargs: (_ for _ in ()).throw(UserApiError(404, "not found", {})))
    with pytest.raises(UserApiError):
        client.get_job("missing")


def test_client_default_retry_status_codes_excludes_5xx() -> None:
    """Test case: test_client_default_retry_status_codes_excludes_5xx."""
    client = OqtopusClient(OqtopusConfig(base_url="http://test"))
    try:
        assert client.retry_status_codes == frozenset({429})
    finally:
        client.close()
