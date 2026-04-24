"""Unit tests for oqtopus-client."""

from __future__ import annotations

import base64
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from oqtopus_client import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from oqtopus_client import (
    rest as models,
)
from oqtopus_client.rest.models.jobs_get_sselog_response import JobsGetSselogResponse


def test_job_result_kind_for_model_sampling() -> None:
    """Test case: test_job_result_kind_for_model_sampling."""
    result = OqtopusJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SAMPLING,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
            result=models.JobsS3JobResult(
                sampling=models.JobsS3SamplingResult(counts={"00": 1}),
            ),
        ),
    )
    assert result.job_id == "job-1"
    assert result.job_type == models.JobsJobType.SAMPLING
    assert result.is_sampling() is True
    assert result.is_estimation() is False


def test_job_result_kind_for_estimation_job_def() -> None:
    """Test case: test_job_result_kind_for_estimation_job_def."""
    result = OqtopusJobResult.from_raw(
        models.JobsJob(
            job_id="job-2",
            name="job-2",
            job_type=models.JobsJobType.ESTIMATION,
            status=models.JobsJobStatus.SUCCEEDED,
            device_id="Kawasaki",
            shots=1,
            job_info=models.JobsJobInfo(
                input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
                result=models.JobsS3JobResult(
                    estimation=models.JobsS3EstimationResult(exp_value=1.0),
                ),
            ),
        )
    )
    assert result.job_type == models.JobsJobType.ESTIMATION
    assert result.is_sampling() is False
    assert result.is_estimation() is True


def test_job_result_from_job_model_like_payload() -> None:
    """Test case: test_job_result_from_job_model_like_payload."""
    submitted_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    job = models.JobsJob(
        job_id="job-3",
        name="job",
        job_type=models.JobsJobType.SAMPLING,
        status=models.JobsJobStatus.SUCCEEDED,
        device_id="Kawasaki",
        shots=100,
        transpiler_info={"backend": "oqtopus"},
        simulator_info={"seed": 7},
        mitigation_info={"enabled": True},
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
            result=models.JobsS3JobResult(
                sampling=models.JobsS3SamplingResult(counts={"01": 10}),
            ),
        ),
        submitted_at=submitted_at,
    )

    result = OqtopusJobResult.from_raw(job)
    assert result.job_id == "job-3"
    assert result.job_type == models.JobsJobType.SAMPLING
    assert result.name == "job"
    assert result.device_id == "Kawasaki"
    assert result.shots == 100
    assert result.transpiler_info == {"backend": "oqtopus"}
    assert result.simulator_info == {"seed": 7}
    assert result.mitigation_info == {"enabled": True}
    assert result.submitted_at == submitted_at
    assert isinstance(result.job_info, models.JobsJobInfo)
    assert isinstance(result.job_info.result, models.JobsS3JobResult)


def test_sampling_result_direct_construction() -> None:
    """Test case: test_sampling_result_direct_construction."""
    result = OqtopusSamplingJobResult(
        job_id="job-5",
        job_type=models.JobsJobType.SAMPLING,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-5",
        device_id="Kawasaki",
        shots=2,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
            result=models.JobsS3JobResult(
                sampling=models.JobsS3SamplingResult(counts={"11": 2}),
            ),
        ),
    )
    assert isinstance(result, OqtopusSamplingJobResult)
    assert result.job_type == models.JobsJobType.SAMPLING
    assert result.get_counts() == {"11": 2}
    assert result.counts_with_integer_keys() == {
        "counts": {3: 2},
        "divided_counts": {},
    }


def test_estimation_result_direct_construction() -> None:
    """Test case: test_estimation_result_direct_construction."""
    result = OqtopusEstimationJobResult(
        job_id="job-6",
        job_type=models.JobsJobType.ESTIMATION,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-6",
        device_id="Kawasaki",
        shots=2,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
            result=models.JobsS3JobResult(
                estimation=models.JobsS3EstimationResult(exp_value=0.75, stds=0.1),
            ),
        ),
    )
    assert isinstance(result, OqtopusEstimationJobResult)
    assert result.job_type == models.JobsJobType.ESTIMATION
    assert result.exp_value == 0.75
    assert result.stds == 0.1
    assert result.get_exp_value() == 0.75
    assert result.get_stds() == 0.1


def test_multi_manual_result_direct_construction() -> None:
    """Test case: test_multi_manual_result_direct_construction."""
    result = OqtopusMultiManualJobResult(
        job_id="job-7",
        job_type=models.JobsJobType.MULTI_MANUAL,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-7",
        device_id="Kawasaki",
        shots=2,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"]),
            result=models.JobsS3JobResult(
                sampling=models.JobsS3SamplingResult(
                    counts={"11": 2},
                    divided_counts={
                        "0": {"11": 1},
                        "1": {"00": 1},
                    },
                ),
            ),
        ),
    )
    assert isinstance(result, OqtopusMultiManualJobResult)
    assert result.job_type == models.JobsJobType.MULTI_MANUAL
    assert result.counts_with_integer_keys() == {
        "counts": {3: 2},
        "divided_counts": {0: {"11": 1}, 1: {"00": 1}},
    }
    assert result.get_divided_counts() == {"0": {3: 1}, "1": {0: 1}}


def test_sse_result_direct_construction() -> None:
    """Test case: test_sse_result_direct_construction."""
    result = OqtopusSseJobResult(
        job_id="job-8",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-8",
        device_id="Kawasaki",
        shots=4,
        job_info=models.JobsJobInfo(
            input=models.JobsS3SubmitJobInfo(program=["print('x')"]),
            result=models.JobsS3JobResult(
                sampling=models.JobsS3SamplingResult(counts={"00": 4}),
            ),
        ),
    )
    assert isinstance(result, OqtopusSseJobResult)
    assert result.job_type == models.JobsJobType.SSE
    assert result.counts_with_integer_keys() == {
        "counts": {0: 4},
        "divided_counts": {},
    }


def test_sse_result_log_helpers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test case: test_sse_result_log_helpers."""
    class _DummyClient:
        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            data = base64.b64encode(f"log-{job_id}".encode()).decode("utf-8")
            return JobsGetSselogResponse(file=data, file_name=f"{job_id}.zip")

    result = OqtopusSseJobResult(
        job_id="job-42",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-42",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_DummyClient(),  # type: ignore[arg-type]
    )
    archive = result.download_log()
    assert isinstance(archive, bytes)
    assert archive == b"log-job-42"
    out = result.download_log(save_dir=tmp_path, persist=True)
    assert isinstance(out, str)
    assert Path(out).exists()
    assert result.read_log_text() == "log-job-42"
    shown = result.show_log()
    assert "log-job-42" in shown
    assert "log-job-42" in capsys.readouterr().out


def test_sse_download_log_default_does_not_write_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test case: test_sse_download_log_default_does_not_write_files."""
    class _DummyClient:
        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            data = base64.b64encode(f"log-{job_id}".encode()).decode("utf-8")
            return JobsGetSselogResponse(file=data, file_name=f"{job_id}.zip")

    monkeypatch.chdir(tmp_path)
    before = {p.name for p in tmp_path.iterdir()}

    result = OqtopusSseJobResult(
        job_id="job-99",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-99",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_DummyClient(),  # type: ignore[arg-type]
    )
    data = result.download_log()
    assert isinstance(data, bytes)
    assert data == b"log-job-99"
    assert result.read_log_text() == "log-job-99"

    after = {p.name for p in tmp_path.iterdir()}
    assert after == before


def test_sse_download_log_rejects_save_options_without_persist(tmp_path: Path) -> None:
    """Test case: test_sse_download_log_rejects_save_options_without_persist."""
    class _DummyClient:
        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            data = base64.b64encode(f"log-{job_id}".encode()).decode("utf-8")
            return JobsGetSselogResponse(file=data, file_name=f"{job_id}.zip")

    result = OqtopusSseJobResult(
        job_id="job-99",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-99",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_DummyClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError):
        result.download_log(save_dir=tmp_path)
    with pytest.raises(ValueError):
        result.download_log(file_name="log.zip")
    with pytest.raises(ValueError):
        result.download_log(overwrite=True)


def test_sse_result_log_helpers_require_client() -> None:
    """Test case: test_sse_result_log_helpers_require_client."""
    result = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
    )
    with pytest.raises(ValueError):
        result.read_log_text()


def test_job_result_repr_and_flags_for_string_job_type() -> None:
    """Test case: test_job_result_repr_and_flags_for_string_job_type."""
    result = OqtopusJobResult(
        job_id="job-x",
        job_type="multi_manual",
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-x",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["OPENQASM 3;"])),
    )
    assert "job-x" in repr(result)
    assert result.is_multi_manual() is True
    assert result.is_sse() is False


def test_sampling_and_estimation_result_fallbacks() -> None:
    """Test case: test_sampling_and_estimation_result_fallbacks."""
    sampling = OqtopusSamplingJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SAMPLING,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info={"program": ["OPENQASM 3;"], "result": {"sampling": {"counts": "bad"}}},
    )
    estimation = OqtopusEstimationJobResult(
        job_id="job-2",
        job_type=models.JobsJobType.ESTIMATION,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-2",
        device_id="Kawasaki",
        shots=1,
        job_info={
            "program": ["OPENQASM 3;"],
            "result": {"estimation": {"exp_value": "bad", "stds": "bad"}},
        },
    )
    assert sampling.get_counts() == {}
    assert estimation.get_exp_value() is None
    assert estimation.get_stds() is None
    assert "OqtopusEstimationJobResult" in repr(estimation)
    assert "OqtopusSamplingJobResult" in repr(sampling)


def test_multi_manual_result_ignores_invalid_divided_counts_entries() -> None:
    """Test case: test_multi_manual_result_ignores_invalid_divided_counts_entries."""
    result = OqtopusMultiManualJobResult(
        job_id="job-3",
        job_type=models.JobsJobType.MULTI_MANUAL,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-3",
        device_id="Kawasaki",
        shots=1,
        job_info={
            "program": ["OPENQASM 3;"],
            "result": {
                "sampling": {"divided_counts": {"good": {"01": 1}, "bad": "x"}},
            },
        },
    )
    assert result.get_divided_counts() == {"good": {1: 1}}
    assert "OqtopusMultiManualJobResult" in repr(result)


def test_sse_download_log_error_paths(tmp_path: Path) -> None:
    """Test case: test_sse_download_log_error_paths."""
    class _NoFileClient:
        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            _ = job_id
            return JobsGetSselogResponse(file=None, file_name=None)

    class _BadBase64Client:
        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            _ = job_id
            return JobsGetSselogResponse(file="*", file_name="x.zip")

    no_file = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_NoFileClient(),
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        no_file.download_log()

    bad_dir_target = tmp_path / "missing" / "file"
    with pytest.raises(ValueError):
        no_file.download_log(save_dir=bad_dir_target)

    bad_dir_target.parent.mkdir(parents=True, exist_ok=True)
    bad_dir_target.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        no_file.download_log(save_dir=bad_dir_target)

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    existing = out_dir / "x.zip"
    existing.write_bytes(b"already")
    bad_base64 = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_BadBase64Client(),
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        bad_base64.download_log(save_dir=out_dir)

    persisted = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_BadBase64Client(),
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        persisted.download_log(persist=True, save_dir=out_dir)


def test_sse_read_log_text_zip_variants() -> None:
    """Test case: test_sse_read_log_text_zip_variants."""
    def _zip_payload(files: dict[str, str]) -> str:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, text in files.items():
                zf.writestr(name, text)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    class _ZipClient:
        def __init__(self, payload: str | None) -> None:
            self.payload = payload

        def get_sselog(self, job_id: str) -> JobsGetSselogResponse:
            _ = job_id
            return JobsGetSselogResponse(file=self.payload, file_name="log.zip")

    no_file = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_ZipClient(None),
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        no_file.read_log_text()

    bad_file = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_ZipClient("*"),
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        bad_file.read_log_text()

    zipped_empty_name = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_ZipClient(_zip_payload({"dir/": ""})),  # type: ignore[arg-type]
    )
    assert zipped_empty_name.read_log_text() == ""

    zipped_multi = OqtopusSseJobResult(
        job_id="job-1",
        job_type=models.JobsJobType.SSE,
        status=models.JobsJobStatus.SUCCEEDED,
        name="job-1",
        device_id="Kawasaki",
        shots=1,
        job_info=models.JobsJobInfo(input=models.JobsS3SubmitJobInfo(program=["print('x')"])),
        client=_ZipClient(_zip_payload({"a.txt": "A", "b.txt": "B"})),  # type: ignore[arg-type]
    )
    text = zipped_multi.read_log_text()
    assert "===== a.txt =====" in text
    assert "===== b.txt =====" in text
    assert "A" in text and "B" in text

    printed: list[str] = []
    assert "OqtopusSseJobResult" in repr(zipped_multi)
    shown = zipped_multi.show_log(print_fn=printed.append)
    assert shown == printed[0]
