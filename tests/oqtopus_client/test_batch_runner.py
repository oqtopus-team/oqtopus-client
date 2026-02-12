from __future__ import annotations

import pytest
import httpx

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec, OqtopusSamplingJobResult, models


def _build_mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if method == "POST" and path == "/jobs":
            payload = request.read().decode("utf-8")
            if "job-1" in payload:
                return httpx.Response(200, json={"job_id": "job-1"})
            if "job-2" in payload:
                return httpx.Response(200, json={"job_id": "job-2"})
            return httpx.Response(200, json={"job_id": "job-from-model"})

        if method == "GET" and path.startswith("/jobs/") and path.endswith("/status"):
            return httpx.Response(
                200,
                json={"job_id": path.split("/")[2], "status": models.JobsJobStatus.SUCCEEDED.value},
            )

        if method == "GET" and path.startswith("/jobs/") and not path.endswith("/status"):
            job_id = path.split("/")[2]
            return httpx.Response(
                200,
                json={
                    "job_id": job_id,
                    "name": "job",
                    "job_type": models.JobsJobType.SAMPLING.value,
                    "status": models.JobsJobStatus.SUCCEEDED.value,
                    "device_id": "Kawasaki",
                    "shots": 1,
                    "job_info": {"program": ["OPENQASM 3; qubit[1] q;"]},
                },
            )

        return httpx.Response(404, json={"message": "not found"})

    return httpx.MockTransport(handler)


def _build_client() -> OqtopusClient:
    return OqtopusClient(
        OqtopusConfig(base_url="https://api.example.com", api_token="token"),
        client=httpx.AsyncClient(transport=_build_mock_transport()),
    )


def test_submit_and_wait_preserves_order() -> None:
    with _build_client() as client:
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

def test_submit_jobs_returns_job_ids() -> None:
    with _build_client() as client:
        responses = client.submit_jobs(
            [OqtopusJobSpec.sampling(name="job-1", device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;")],
            max_workers=1,
        )
        assert [response.job_id for response in responses] == ["job-1"]


def test_submit_jobs_accepts_job_spec() -> None:
    with _build_client() as client:
        responses = client.submit_jobs(
            [OqtopusJobSpec.sampling(device_id="Kawasaki", program="OPENQASM 3; qubit[1] q;")],
            max_workers=1,
        )
        assert len(responses) == 1


def test_run_jobs_batch_preserves_order() -> None:
    with _build_client() as client:
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
        assert isinstance(results[0], OqtopusSamplingJobResult)


def test_run_jobs_batch_rejects_non_jobspec() -> None:
    with _build_client() as client:
        with pytest.raises(TypeError):
            client.run_jobs_batch([{"job_id": "job-1"}], submit_workers=1, wait_workers=1, timeout=1.0)  # type: ignore[list-item]


def test_client_parallel_helpers_validate_worker_count() -> None:
    with _build_client() as client:
        with pytest.raises(ValueError):
            client.submit_jobs([], max_workers=0)
        with pytest.raises(ValueError):
            client.wait_for_jobs([], max_workers=0)
        with pytest.raises(ValueError):
            client.run_jobs_batch([], submit_workers=0)
