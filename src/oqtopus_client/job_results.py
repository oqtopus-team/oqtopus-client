"""Core module for oqtopus-client."""

from __future__ import annotations

import base64
import binascii
import io
import zipfile
from collections.abc import Callable
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from . import models

if TYPE_CHECKING:
    from .client import OqtopusClient

SamplingPayload = models.JobsSamplingResult | Mapping[str, Any] | None
EstimationPayload = models.JobsEstimationResult | Mapping[str, Any] | None


class OqtopusJobResult:
    """SDK result object for a job's state and execution output payloads."""

    def __init__(
        self,
        raw: models.JobsJobResult | Mapping[str, Any] | None,
        *,
        job_id: str | None = None,
        job_type: models.JobsJobType | str | None = None,
        status: models.JobsJobStatus | str | None = None,
        job_info: models.JobsJobInfo | Mapping[str, Any] | None = None,
        transpile_result: models.JobsTranspileResult | Mapping[str, Any] | None = None,
        message: str | None = None,
        execution_time: float | int | None = None,
        client: OqtopusClient | None = None,
    ) -> None:
        self._raw = raw
        self._job_id = job_id
        self._job_type = self._normalize_job_type(job_type) or self._infer_job_type(raw)
        self._status = self._normalize_status(status)
        self._job_info = job_info
        self._transpile_result = transpile_result
        self._message = message
        self._execution_time = execution_time
        self._client = client

    @property
    def raw(self) -> models.JobsJobResult | Mapping[str, Any] | None:
        """Return the original result payload as received from API/models."""
        return self._raw

    @property
    def job_id(self) -> str | None:
        """Return related job id when known."""
        return self._job_id

    @property
    def job_type(self) -> models.JobsJobType | None:
        """Return related job type when known."""
        return self._job_type

    @property
    def status(self) -> models.JobsJobStatus | None:
        """Return related job status when known."""
        return self._status

    @property
    def job_info(self) -> models.JobsJobInfo | Mapping[str, Any] | None:
        """Return related job_info payload when known."""
        return self._job_info

    @property
    def transpile_result(self) -> models.JobsTranspileResult | Mapping[str, Any] | None:
        """Return related transpile result when known."""
        return self._transpile_result

    @property
    def message(self) -> str | None:
        """Return related message when known."""
        return self._message

    @property
    def execution_time(self) -> float | int | None:
        """Return related execution time when known."""
        return self._execution_time

    def is_sampling(self) -> bool:
        """Return ``True`` when this result belongs to a sampling job."""
        return self.job_type == models.JobsJobType.SAMPLING

    def is_estimation(self) -> bool:
        """Return ``True`` when this result belongs to an estimation job."""
        return self.job_type == models.JobsJobType.ESTIMATION

    def is_multi_manual(self) -> bool:
        """Return ``True`` when this result belongs to a multi-manual job."""
        return self.job_type == models.JobsJobType.MULTI_MANUAL

    def is_sse(self) -> bool:
        """Return ``True`` when this result belongs to an SSE job."""
        return self.job_type == models.JobsJobType.SSE

    @staticmethod
    def _normalize_job_type(
        job_type: models.JobsJobType | str | None,
    ) -> models.JobsJobType | None:
        if isinstance(job_type, models.JobsJobType):
            return job_type
        if isinstance(job_type, str):
            try:
                return models.JobsJobType(job_type)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_status(
        status: models.JobsJobStatus | str | None,
    ) -> models.JobsJobStatus | None:
        if isinstance(status, models.JobsJobStatus):
            return status
        if isinstance(status, str):
            try:
                return models.JobsJobStatus(status)
            except ValueError:
                return None
        return None

    @staticmethod
    def _infer_job_type(
        raw: models.JobsJobResult | Mapping[str, Any] | None,
    ) -> models.JobsJobType | None:
        if raw is None:
            return None
        if isinstance(raw, models.JobsJobResult):
            if raw.sampling is not None:
                return models.JobsJobType.SAMPLING
            if raw.estimation is not None:
                return models.JobsJobType.ESTIMATION
            return None
        sampling = raw.get("sampling")
        estimation = raw.get("estimation")
        if sampling is not None:
            return models.JobsJobType.SAMPLING
        if estimation is not None:
            return models.JobsJobType.ESTIMATION
        return None

    def __repr__(self) -> str:
        return (
            f"OqtopusJobResult("
            f"job_id={self.job_id!r}, job_type={self.job_type!r}, status={self.status!r})"
        )

    @property
    def sampling(self) -> SamplingPayload:
        """Return sampling payload when result is sampling-like."""
        raw = self._raw
        if isinstance(raw, models.JobsJobResult):
            return raw.sampling
        if isinstance(raw, Mapping):
            sampling = raw.get("sampling")
            return sampling if isinstance(sampling, Mapping) else None
        return None

    @property
    def estimation(self) -> EstimationPayload:
        """Return estimation payload when result is estimation-like."""
        raw = self._raw
        if isinstance(raw, models.JobsJobResult):
            return raw.estimation
        if isinstance(raw, Mapping):
            estimation = raw.get("estimation")
            return estimation if isinstance(estimation, Mapping) else None
        return None

class OqtopusSamplingJobResult(OqtopusJobResult):
    """Specialized SDK result object for sampling jobs."""

    @property
    def sampling(self) -> SamplingPayload:
        """Return sampling payload only, or ``None`` when unavailable."""
        raw = self.raw
        if isinstance(raw, models.JobsJobResult):
            return raw.sampling
        if isinstance(raw, Mapping):
            sampling = raw.get("sampling")
            if isinstance(sampling, Mapping):
                return sampling
        return None

    def normalized_counts(self) -> dict[str, dict[int, Any]]:
        """Normalize bitstring keys into integer keys for sampling payload."""
        from .result_utils import normalize_sampling_result

        return normalize_sampling_result(self.sampling)

    def get_counts(self) -> dict[str, Any]:
        """Return raw counts with original bitstring keys."""
        sampling = self.sampling
        if isinstance(sampling, models.JobsSamplingResult):
            return dict(sampling.counts or {})
        if isinstance(sampling, Mapping):
            counts = sampling.get("counts")
            if isinstance(counts, Mapping):
                return {str(k): v for k, v in counts.items()}
        return {}

    def __repr__(self) -> str:
        return f"OqtopusSamplingJobResult(job_id={self.job_id!r})"


class OqtopusEstimationJobResult(OqtopusJobResult):
    """Specialized SDK result object for estimation jobs."""

    @property
    def estimation(self) -> EstimationPayload:
        """Return estimation payload only, or ``None`` when unavailable."""
        raw = self.raw
        if isinstance(raw, models.JobsJobResult):
            return raw.estimation
        if isinstance(raw, Mapping):
            estimation = raw.get("estimation")
            if isinstance(estimation, Mapping):
                return estimation
        return None

    @property
    def exp_value(self) -> float | None:
        """Alias of :meth:`get_exp_value`."""
        return self.get_exp_value()

    @property
    def stds(self) -> float | None:
        """Alias of :meth:`get_stds`."""
        return self.get_stds()

    def get_exp_value(self) -> float | None:
        """Return estimation exp_value."""
        estimation = self.estimation
        if isinstance(estimation, models.JobsEstimationResult):
            return estimation.exp_value
        if isinstance(estimation, Mapping):
            exp_value = estimation.get("exp_value")
            return float(exp_value) if isinstance(exp_value, (int, float)) else None
        return None

    def get_stds(self) -> float | None:
        """Return estimation stds."""
        estimation = self.estimation
        if isinstance(estimation, models.JobsEstimationResult):
            return estimation.stds
        if isinstance(estimation, Mapping):
            stds = estimation.get("stds")
            return float(stds) if isinstance(stds, (int, float)) else None
        return None

    def __repr__(self) -> str:
        return f"OqtopusEstimationJobResult(job_id={self.job_id!r})"


class OqtopusMultiManualJobResult(OqtopusSamplingJobResult):
    """Specialized SDK result object for multi_manual jobs."""

    def get_divided_counts(self) -> dict[str, dict[int, Any]]:
        """Return normalized counts per sub-result from `divided_counts`."""
        sampling = self.sampling
        if isinstance(sampling, models.JobsSamplingResult):
            divided_counts = sampling.divided_counts
        elif isinstance(sampling, Mapping):
            divided_counts = sampling.get("divided_counts")
        else:
            divided_counts = None

        if not isinstance(divided_counts, Mapping):
            return {}

        from .result_utils import bitstring_dict_to_int_keys

        normalized: dict[str, dict[int, Any]] = {}
        for result_key, counts in divided_counts.items():
            if not isinstance(counts, Mapping):
                continue
            normalized[str(result_key)] = bitstring_dict_to_int_keys(
                {str(k): v for k, v in counts.items()}
            )
        return normalized

    def __repr__(self) -> str:
        return f"OqtopusMultiManualJobResult(job_id={self.job_id!r})"


class OqtopusSseJobResult(OqtopusSamplingJobResult):
    """Specialized SDK result object for sse jobs."""

    def _get_log_archive_bytes(self) -> tuple[bytes, str]:
        client = self._require_client()
        if self.job_id is None:
            raise ValueError("job_id is required for SSE log operations.")
        response = client.get_sselog(self.job_id)
        if response.file is None or response.file_name is None:
            raise ValueError("SSE log response does not contain valid file data.")
        try:
            decoded = base64.b64decode(response.file, validate=True)
        except binascii.Error as e:
            raise ValueError("SSE log file field is not valid base64 data.") from e
        return decoded, response.file_name

    @staticmethod
    def _write_archive(
        archive_bytes: bytes,
        *,
        save_dir: str | Path | None,
        file_name: str,
        overwrite: bool,
    ) -> str:
        out_dir = Path.cwd() if save_dir is None else Path(save_dir)
        if not out_dir.exists():
            raise ValueError(f"The destination path does not exist: {out_dir}")
        if not out_dir.is_dir():
            raise ValueError(f"The destination path is not a directory: {out_dir}")

        out_path = out_dir / file_name
        if out_path.exists() and not overwrite:
            raise ValueError(f"The file already exists: {out_path}")
        out_path.write_bytes(archive_bytes)
        return str(out_path)

    def download_log(
        self,
        *,
        save_dir: str | Path | None = None,
        file_name: str | None = None,
        overwrite: bool = False,
        persist: bool = False,
    ) -> bytes | str:
        """Download SSE archive from `/jobs/{job_id}/sselog`.

        Default behavior keeps processing in-memory and returns archive bytes.
        Set `persist=True` to write the archive file to disk and return its path.
        For compatibility, specifying `save_dir` / `file_name` / `overwrite=True`
        also enables persistence.
        """
        archive_bytes, default_file_name = self._get_log_archive_bytes()
        should_persist = persist or save_dir is not None or file_name is not None or overwrite
        if not should_persist:
            return archive_bytes
        return self._write_archive(
            archive_bytes,
            save_dir=save_dir,
            file_name=file_name or default_file_name,
            overwrite=overwrite,
        )

    def read_log_text(
        self,
        *,
        encoding: str = "utf-8",
        errors: str = "replace",
    ) -> str:
        """Decode SSE log response and return readable text."""
        decoded, _ = self._get_log_archive_bytes()

        try:
            with zipfile.ZipFile(io.BytesIO(decoded), mode="r") as zf:
                names = [name for name in zf.namelist() if not name.endswith("/")]
                if not names:
                    return ""
                chunks: list[str] = []
                for name in names:
                    text = zf.read(name).decode(encoding, errors=errors)
                    chunks.append(f"===== {name} =====\n{text}")
                return "\n".join(chunks).rstrip()
        except zipfile.BadZipFile:
            return decoded.decode(encoding, errors=errors)

    def show_log(
        self,
        *,
        encoding: str = "utf-8",
        errors: str = "replace",
        print_fn: Callable[[str], Any] = print,
    ) -> str:
        """Read SSE log text and print it. Returns printed text."""
        text = self.read_log_text(
            encoding=encoding,
            errors=errors,
        )
        print_fn(text)
        return text

    def _require_client(self) -> OqtopusClient:
        if self._client is None:
            raise ValueError("SSE log operations require a client-bound OqtopusSseJobResult.")
        return self._client

    def __repr__(self) -> str:
        return f"OqtopusSseJobResult(job_id={self.job_id!r})"
