"""Unit tests for oqtopus-client."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
    OqtopusSamplingJobResult,
)
from oqtopus_client import rest as models


def _job(job_id: str) -> models.JobsJobDef:
    return models.JobsJobDef(
        job_id=job_id,
        name="job",
        job_type=models.JobsJobType.SAMPLING,
        status=models.JobsJobStatus.SUCCEEDED,
        device_id="K",
        shots=1,
        job_info=models.JobsJobInfo(
            program=["OPENQASM 3; qubit[1] q;"],
            result=models.JobsJobResult(sampling=models.JobsSamplingResult(counts={"00": 1})),
        ),
    )


def _build_client() -> OqtopusClient:
    client = object.__new__(OqtopusClient)

    def fake_call(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "submit_job":
            spec = args[0]
            if isinstance(spec, OqtopusJobSpec) and spec.name:
                return models.JobsSubmitJobResponse(job_id=spec.name)
            return models.JobsSubmitJobResponse(job_id="job-from-spec")
        if name == "wait_for_job":
            return _job(args[0])
        raise AssertionError(name)

    client._call = fake_call  # type: ignore[assignment,method-assign]
    client._async = Mock()
    client._runtime = Mock()
    client._closed = False
    client.base_url = OqtopusConfig(base_url="https://api.example.com").base_url
    return client


def test_submit_and_wait_preserves_order() -> None:
    """Test case: test_submit_and_wait_preserves_order."""
    client = _build_client()

    responses = client.submit_jobs(
        [
            OqtopusJobSpec.sampling(name="job-1", device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            OqtopusJobSpec.sampling(name="job-2", device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
        ],
        max_workers=2,
    )
    assert [r.job_id for r in responses] == ["job-1", "job-2"]

    jobs = client.wait_for_jobs(["job-2", "job-1"], timeout=1.0, max_workers=2)
    assert [job.job_id for job in jobs] == ["job-2", "job-1"]
    assert isinstance(jobs[0], OqtopusSamplingJobResult)


def test_run_jobs_batch_preserves_order() -> None:
    """Test case: test_run_jobs_batch_preserves_order."""
    client = _build_client()

    results = client.run_jobs_batch(
        [
            OqtopusJobSpec.sampling(name="job-2", device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
            OqtopusJobSpec.sampling(name="job-1", device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;"),
        ],
        submit_workers=2,
        wait_workers=2,
        timeout=1.0,
    )
    assert [result.job_id for result in results] == ["job-2", "job-1"]


def test_parallel_helpers_validate_worker_count() -> None:
    """Test case: test_parallel_helpers_validate_worker_count."""
    client = _build_client()

    with pytest.raises(ValueError):
        client.submit_jobs([], max_workers=0)
    with pytest.raises(ValueError):
        client.wait_for_jobs([], max_workers=0)
    with pytest.raises(ValueError):
        client.run_jobs_batch([], submit_workers=0)


def test_run_jobs_batch_rejects_non_jobspec() -> None:
    """Test case: test_run_jobs_batch_rejects_non_jobspec."""
    client = _build_client()

    with pytest.raises(TypeError):
        client.run_jobs_batch([{"job_id": "job-1"}], submit_workers=1, wait_workers=1, timeout=1.0)  # type: ignore[list-item]
