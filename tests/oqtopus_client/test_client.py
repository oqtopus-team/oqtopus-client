from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from oqtopus_client import (
    OqtopusClient,
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusJobSpec,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
    models,
)
from oqtopus_client.errors import UserApiError


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
    )


def _build_client_with_fake_call(fake_call: Any) -> OqtopusClient:
    client = object.__new__(OqtopusClient)
    client._call = fake_call  # type: ignore[assignment,method-assign]
    client._async = Mock()
    client._runtime = Mock()
    client._closed = False
    return client


def test_submit_job_accepts_job_spec() -> None:
    called: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        called.append((name, args, kwargs))
        return models.JobsSubmitJobResponse(job_id="job-1")

    client = _build_client_with_fake_call(fake_call)
    res = client.submit_job(OqtopusJobSpec.sampling(device_id="K", program="OPENQASM 3; qubit[1] q;"))

    assert res.job_id == "job-1"
    assert called[0][0] == "submit_job"


def test_get_job_returns_extended_job_result() -> None:
    client = _build_client_with_fake_call(lambda name, *args, **kwargs: _job(models.JobsJobType.SAMPLING))

    result = client.get_job("job-1")

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-1"
    assert result.status == models.JobsJobStatus.SUCCEEDED
    assert result.execution_time == 1.23
    assert result.message == "queued"
    assert isinstance(result.transpile_result, models.JobsTranspileResult)


def test_result_aliases_return_job_result() -> None:
    client = _build_client_with_fake_call(lambda name, *args, **kwargs: _job(models.JobsJobType.SAMPLING))

    assert isinstance(client.get_job_result("job-1"), OqtopusJobResult)
    assert isinstance(client.result("job-1"), OqtopusJobResult)
    assert isinstance(client.refresh("job-1"), OqtopusJobResult)


def test_run_helpers_return_typed_results() -> None:
    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        mapping = {
            "run_job": models.JobsJobType.SAMPLING,
            "run_sampling": models.JobsJobType.SAMPLING,
            "run_estimation": models.JobsJobType.ESTIMATION,
            "run_multi_manual": models.JobsJobType.MULTI_MANUAL,
            "run_sse": models.JobsJobType.SSE,
            "run_sse_file": models.JobsJobType.SSE,
        }
        return _job(mapping[name])

    client = _build_client_with_fake_call(fake_call)

    assert isinstance(client.run_job(OqtopusJobSpec.sampling(device_id="K", program="x")), OqtopusJobResult)
    assert isinstance(client.run_sampling(OqtopusJobSpec.sampling(device_id="K", program="x")), OqtopusSamplingJobResult)
    assert isinstance(
        client.run_estimation(OqtopusJobSpec.estimation(device_id="K", program="x", operator=[{"pauli": "Z0", "coeff": 1}])),
        OqtopusEstimationJobResult,
    )
    assert isinstance(client.run_multi_manual(OqtopusJobSpec.multi_manual(device_id="K", program="x")), OqtopusMultiManualJobResult)
    assert isinstance(client.run_sse(OqtopusJobSpec.sse(device_id="K", program="print('x')")), OqtopusSseJobResult)


def test_list_jobs_and_filters_passthrough() -> None:
    now = datetime.now(timezone.utc)

    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        assert name == "list_jobs"
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
            )
        ]

    client = _build_client_with_fake_call(fake_call)
    jobs = client.list_jobs(end_time=now)
    assert len(jobs) == 1


def test_status_and_cancel_helpers() -> None:
    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "get_job_status":
            return models.JobsGetJobStatusResponse(job_id=args[0], status=models.JobsJobStatus.SUCCEEDED)
        if name == "cancel_job":
            return models.SuccessSuccessResponse(message="ok")
        raise AssertionError(name)

    client = _build_client_with_fake_call(fake_call)

    assert client.status("job-1") == models.JobsJobStatus.SUCCEEDED
    assert client.is_finished("job-1") is True
    assert client.cancel("job-1").message == "ok"


def test_api_error_propagates() -> None:
    client = _build_client_with_fake_call(lambda name, *args, **kwargs: (_ for _ in ()).throw(UserApiError(404, "not found", {})))
    with pytest.raises(UserApiError):
        client.get_job("missing")
