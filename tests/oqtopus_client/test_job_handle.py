from __future__ import annotations

from typing import Any, cast

import pytest

from oqtopus_client import (
    OqtopusJobResult,
    OqtopusJobHandle,
    OqtopusJobSpec,
    OqtopusSamplingJobResult,
    models,
)


class _DummyClient:
    def __init__(self, job_type: models.JobsJobType = models.JobsJobType.SAMPLING) -> None:
        self.cancelled: list[str] = []
        self.job_type = job_type

    def submit_job(self, body: OqtopusJobSpec) -> OqtopusJobHandle:
        _ = body
        return OqtopusJobHandle(cast(Any, self), "job-from-spec")

    def get_job_status(self, job_id: str) -> Any:
        return models.JobsGetJobStatusResponse(job_id=job_id, status=models.JobsJobStatus.SUCCEEDED)

    def wait_for_job(
        self,
        job_id: str,
        *,
        interval: float,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
    ) -> OqtopusJobResult:
        _ = interval, interval_backoff, max_interval, timeout, terminal_statuses, failure_statuses
        return self._job(job_id)

    def cancel_job(self, job_id: str) -> models.SuccessSuccessResponse:
        self.cancelled.append(job_id)
        return models.SuccessSuccessResponse(message="ok")

    def get_job_result(self, job_id: str) -> OqtopusJobResult:
        return self._job(job_id)

    def _job(self, job_id: str) -> OqtopusJobResult:
        if self.job_type in {models.JobsJobType.SAMPLING, models.JobsJobType.MULTI_MANUAL, models.JobsJobType.SSE}:
            result = models.JobsJobResult(sampling=models.JobsSamplingResult(counts={"00": 1}))
        else:
            result = models.JobsJobResult(estimation=models.JobsEstimationResult(exp_value=1.0, stds=0.1))
        if self.job_type == models.JobsJobType.ESTIMATION:
            return OqtopusJobResult(result, job_id=job_id, job_type=self.job_type, client=cast(Any, self))
        return OqtopusSamplingJobResult(result, job_id=job_id, job_type=self.job_type, client=cast(Any, self))


def test_wrapper_can_be_created_from_submission() -> None:
    client: Any = _DummyClient()
    submitted_job = client.submit_job(OqtopusJobSpec.sampling(device_id="Kawasaki", program="x"))
    job = OqtopusJobHandle(client, submitted_job.job_id)
    assert isinstance(job, OqtopusJobHandle)
    assert job.job_id == "job-from-spec"


def test_wrapper_status_wait_cancel_and_refresh() -> None:
    client: Any = _DummyClient()
    job = OqtopusJobHandle(client, "job-1")

    assert job.status() == models.JobsJobStatus.SUCCEEDED
    assert job.is_finished() is True
    assert job.wait(interval=0.1, timeout=1.0).job_id == "job-1"
    assert job.refresh().job_id == "job-1"
    assert job.cancel().message == "ok"
    assert client.cancelled == ["job-1"]


def test_wrapper_result_returns_typed_result_object() -> None:
    client: Any = _DummyClient()
    job = OqtopusJobHandle(client, "job-1")

    result = job.get_result(interval=0.1, timeout=1.0)
    current = job.get_current_result()

    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_id == "job-1"
    assert result.normalized_counts() == {"counts": {0: 1}, "divided_counts": {}}
    assert isinstance(current, OqtopusSamplingJobResult)


def test_wrapper_get_result_returns_job_type_specific_result() -> None:
    sampling_job = OqtopusJobHandle(cast(Any, _DummyClient(models.JobsJobType.SAMPLING)), "job-1")
    estimation_job = OqtopusJobHandle(cast(Any, _DummyClient(models.JobsJobType.ESTIMATION)), "job-2")
    multi_manual_job = OqtopusJobHandle(cast(Any, _DummyClient(models.JobsJobType.MULTI_MANUAL)), "job-3")
    sse_job = OqtopusJobHandle(cast(Any, _DummyClient(models.JobsJobType.SSE)), "job-4")

    assert isinstance(sampling_job.get_result(timeout=1.0), OqtopusSamplingJobResult)
    assert estimation_job.get_result(timeout=1.0).job_type == models.JobsJobType.ESTIMATION
    assert multi_manual_job.get_result(timeout=1.0).job_type == models.JobsJobType.MULTI_MANUAL
    assert sse_job.get_result(timeout=1.0).job_type == models.JobsJobType.SSE


def test_wrapper_validates_job_id() -> None:
    client: Any = _DummyClient()
    with pytest.raises(ValueError):
        OqtopusJobHandle(client, "")


def test_wrapper_repr_and_unknown_job_type_fallback() -> None:
    class _UnknownClient(_DummyClient):
        def _job(self, job_id: str) -> Any:
            return OqtopusJobResult(None, job_id=job_id, job_type="unknown", client=cast(Any, self))

    job = OqtopusJobHandle(cast(Any, _UnknownClient()), "job-unknown")
    result = job.get_result(timeout=1.0)
    assert result.job_id == "job-unknown"
    assert "job-unknown" in repr(job)
