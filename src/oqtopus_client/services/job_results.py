"""Core module for oqtopus-client."""

from __future__ import annotations

import base64
import binascii
import io
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import rest as models

if TYPE_CHECKING:
    from datetime import datetime

    from typing_extensions import Self

    from .client import OqtopusClient

SamplingPayload = models.JobsSamplingResult | Mapping[str, Any] | None
EstimationPayload = models.JobsEstimationResult | Mapping[str, Any] | None


class OqtopusJobResult:  # noqa: PLR0904
    """SDK result object for a job's state and execution output payloads."""

    _raw: models.JobsJobResult | Mapping[str, Any] | None
    _job_id: str | None
    _job_type: models.JobsJobType | None
    _status: models.JobsJobStatus | None
    _name: str | None
    _description: str | None
    _device_id: str | None
    _shots: int | None
    _job_info: models.JobsJobInfo | Mapping[str, Any] | None
    _transpiler_info: Mapping[str, Any] | None
    _simulator_info: Mapping[str, Any] | None
    _mitigation_info: Mapping[str, Any] | None
    _transpile_result: models.JobsTranspileResult | Mapping[str, Any] | None
    _message: str | None
    _execution_time: float | None
    _submitted_at: datetime | None
    _ready_at: datetime | None
    _running_at: datetime | None
    _ended_at: datetime | None
    _client: object | None

    def __init__(
        self,
        raw: models.JobsJobResult | Mapping[str, Any] | None,
        *,
        job_id: str,
        job_type: models.JobsJobType | str,
        status: models.JobsJobStatus | str,
        name: str,
        description: str | None = None,
        device_id: str,
        shots: int,
        job_info: models.JobsJobInfo | Mapping[str, Any],
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
        transpile_result: models.JobsTranspileResult | Mapping[str, Any] | None = None,
        message: str | None = None,
        execution_time: float | None = None,
        submitted_at: datetime | None = None,
        ready_at: datetime | None = None,
        running_at: datetime | None = None,
        ended_at: datetime | None = None,
        client: object | None = None,
    ) -> None:
        """Initialize a job result wrapper from raw API payload and metadata.

        Raises:
            ValueError: If metadata is invalid or conflicts with ``raw``.

        """
        self._validate_raw_metadata_conflicts(
            raw=raw,
            job_id=job_id,
            job_type=job_type,
            status=status,
            name=name,
            description=description,
            device_id=device_id,
            shots=shots,
            submitted_at=submitted_at,
            ready_at=ready_at,
            running_at=running_at,
            ended_at=ended_at,
        )
        self._raw = raw
        self._job_id = job_id
        self._job_type = self._normalize_job_type(job_type)
        self._status = self._normalize_status(status)
        self._name = name
        self._description = description
        self._device_id = device_id
        self._shots = shots
        self._job_info = job_info
        self._transpiler_info = transpiler_info
        self._simulator_info = simulator_info
        self._mitigation_info = mitigation_info
        self._transpile_result = transpile_result
        self._message = message
        self._execution_time = execution_time
        self._submitted_at = submitted_at
        self._ready_at = ready_at
        self._running_at = running_at
        self._ended_at = ended_at
        self._client = client

        if self._job_type is None:
            raise ValueError(f"Invalid job_type: {job_type!r}")
        if self._status is None:
            raise ValueError(f"Invalid status: {status!r}")

    @classmethod
    def from_raw(
        cls,
        raw: models.JobsJobResult | Mapping[str, Any] | None,
        *,
        job_id: str | None = None,
        job_type: models.JobsJobType | str | None = None,
        status: models.JobsJobStatus | str | None = None,
        name: str | None = None,
        description: str | None = None,
        device_id: str | None = None,
        shots: int | None = None,
        job_info: models.JobsJobInfo | Mapping[str, Any] | None = None,
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
        transpile_result: models.JobsTranspileResult | Mapping[str, Any] | None = None,
        message: str | None = None,
        execution_time: float | None = None,
        submitted_at: datetime | None = None,
        ready_at: datetime | None = None,
        running_at: datetime | None = None,
        ended_at: datetime | None = None,
        client: object | None = None,
    ) -> Self:
        """Build a fallback result object from partial raw payload metadata.

        Returns:
            A result object that may contain partial metadata.

        """
        cls._validate_raw_metadata_conflicts(
            raw=raw,
            job_id=job_id,
            job_type=job_type,
            status=status,
            name=name,
            description=description,
            device_id=device_id,
            shots=shots,
            submitted_at=submitted_at,
            ready_at=ready_at,
            running_at=running_at,
            ended_at=ended_at,
        )
        normalized_job_type = cls._normalize_job_type(
            job_type,
        ) or cls._infer_job_type(raw)
        normalized_status = cls._normalize_status(status)
        result = cls.__new__(cls)
        result._assign_partial_metadata(  # noqa: SLF001
            raw=raw,
            job_id=job_id,
            job_type=normalized_job_type,
            status=normalized_status,
            name=name,
            description=description,
            device_id=device_id,
            shots=shots,
            job_info=job_info,
            transpiler_info=transpiler_info,
            simulator_info=simulator_info,
            mitigation_info=mitigation_info,
            transpile_result=transpile_result,
            message=message,
            execution_time=execution_time,
            submitted_at=submitted_at,
            ready_at=ready_at,
            running_at=running_at,
            ended_at=ended_at,
            client=client,
        )
        return result

    def _assign_partial_metadata(
        self,
        *,
        raw: models.JobsJobResult | Mapping[str, Any] | None,
        job_id: str | None,
        job_type: models.JobsJobType | None,
        status: models.JobsJobStatus | None,
        name: str | None,
        description: str | None,
        device_id: str | None,
        shots: int | None,
        job_info: models.JobsJobInfo | Mapping[str, Any] | None,
        transpiler_info: Mapping[str, Any] | None,
        simulator_info: Mapping[str, Any] | None,
        mitigation_info: Mapping[str, Any] | None,
        transpile_result: models.JobsTranspileResult | Mapping[str, Any] | None,
        message: str | None,
        execution_time: float | None,
        submitted_at: datetime | None,
        ready_at: datetime | None,
        running_at: datetime | None,
        ended_at: datetime | None,
        client: object | None,
    ) -> None:
        self._raw = raw
        self._job_id = job_id
        self._job_type = job_type
        self._status = status
        self._name = name
        self._description = description
        self._device_id = device_id
        self._shots = shots
        self._job_info = job_info
        self._transpiler_info = transpiler_info
        self._simulator_info = simulator_info
        self._mitigation_info = mitigation_info
        self._transpile_result = transpile_result
        self._message = message
        self._execution_time = execution_time
        self._submitted_at = submitted_at
        self._ready_at = ready_at
        self._running_at = running_at
        self._ended_at = ended_at
        self._client = client

    @classmethod
    def _validate_raw_metadata_conflicts(
        cls,
        *,
        raw: models.JobsJobResult | Mapping[str, Any] | None,
        job_id: str | None,
        job_type: models.JobsJobType | str | None,
        status: models.JobsJobStatus | str | None,
        name: str | None,
        description: str | None,
        device_id: str | None,
        shots: int | None,
        submitted_at: datetime | None,
        ready_at: datetime | None,
        running_at: datetime | None,
        ended_at: datetime | None,
    ) -> None:
        if not isinstance(raw, Mapping):
            return

        cls._validate_raw_value("job_id", raw, job_id)
        cls._validate_raw_value("name", raw, name)
        cls._validate_raw_value("description", raw, description)
        cls._validate_raw_value("device_id", raw, device_id)
        cls._validate_raw_value("shots", raw, shots)
        cls._validate_raw_value("submitted_at", raw, submitted_at)
        cls._validate_raw_value("ready_at", raw, ready_at)
        cls._validate_raw_value("running_at", raw, running_at)
        cls._validate_raw_value("ended_at", raw, ended_at)

        normalized_job_type = cls._normalize_job_type(job_type)
        if normalized_job_type is not None:
            cls._validate_raw_value("job_type", raw, normalized_job_type)

        normalized_status = cls._normalize_status(status)
        if normalized_status is not None:
            cls._validate_raw_value("status", raw, normalized_status)

    @staticmethod
    def _validate_raw_value(
        key: str,
        raw: Mapping[str, Any],
        provided: object,
    ) -> None:
        if provided is None or key not in raw:
            return

        raw_value = raw[key]
        if not OqtopusJobResult._is_comparable_metadata_value(provided, raw_value):
            return
        if raw_value != provided:
            raise ValueError(
                f"Conflicting values for '{key}': "
                f"raw={raw_value!r}, provided={provided!r}",
            )

    @staticmethod
    def _is_comparable_metadata_value(
        provided: object,
        raw_value: object,
    ) -> bool:
        return isinstance(raw_value, type(provided))

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
        """Return related job status when known.

        Possible values are ``submitted``, ``ready``, ``running``,
        ``succeeded``, ``failed``, and ``cancelled``.

        For helpers that wait for completion such as ``wait()`` and ``run_*()``,
        the returned status is typically ``succeeded``, ``failed``, or
        ``cancelled``.

        """
        return self._status

    @property
    def name(self) -> str | None:
        """Return related job name when known."""
        return self._name

    @property
    def description(self) -> str | None:
        """Return related job description when known."""
        return self._description

    @property
    def device_id(self) -> str | None:
        """Return related device id when known."""
        return self._device_id

    @property
    def shots(self) -> int | None:
        """Return related shots when known."""
        return self._shots

    @property
    def job_info(self) -> models.JobsJobInfo | Mapping[str, Any] | None:
        """Return related job_info payload when known."""
        return self._job_info

    @property
    def transpiler_info(self) -> Mapping[str, Any] | None:
        """Return related transpiler info when known."""
        return self._transpiler_info

    @property
    def simulator_info(self) -> Mapping[str, Any] | None:
        """Return related simulator info when known."""
        return self._simulator_info

    @property
    def mitigation_info(self) -> Mapping[str, Any] | None:
        """Return related mitigation info when known."""
        return self._mitigation_info

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

    @property
    def submitted_at(self) -> datetime | None:
        """Return related submission time when known."""
        return self._submitted_at

    @property
    def ready_at(self) -> datetime | None:
        """Return related ready time when known."""
        return self._ready_at

    @property
    def running_at(self) -> datetime | None:
        """Return related running time when known."""
        return self._running_at

    @property
    def ended_at(self) -> datetime | None:
        """Return related end time when known."""
        return self._ended_at

    def is_sampling(self) -> bool:
        """Return ``True`` when this result belongs to a sampling job.

        Returns:
            ``True`` when the job type is sampling.

        """
        return self.job_type == models.JobsJobType.SAMPLING

    def is_estimation(self) -> bool:
        """Return ``True`` when this result belongs to an estimation job.

        Returns:
            ``True`` when the job type is estimation.

        """
        return self.job_type == models.JobsJobType.ESTIMATION

    def is_multi_manual(self) -> bool:
        """Return ``True`` when this result belongs to a multi-manual job.

        Returns:
            ``True`` when the job type is multi-manual.

        """
        return self.job_type == models.JobsJobType.MULTI_MANUAL

    def is_sse(self) -> bool:
        """Return ``True`` when this result belongs to an SSE job.

        Returns:
            ``True`` when the job type is SSE.

        """
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
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return (
            "OqtopusJobResult("
            f"job_id={self.job_id!r}, "
            f"job_type={self.job_type!r}, "
            f"status={self.status!r})"
        )

    @property
    def sampling(self) -> SamplingPayload:
        """Return sampling payload when result is sampling-like.

        Returns:
            Sampling payload when available.

        """
        raw = self._raw
        if isinstance(raw, models.JobsJobResult):
            return raw.sampling
        if isinstance(raw, Mapping):
            sampling = raw.get("sampling")
            return sampling if isinstance(sampling, Mapping) else None
        return None

    @property
    def estimation(self) -> EstimationPayload:
        """Return estimation payload when result is estimation-like.

        Returns:
            Estimation payload when available.

        """
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
        """Return sampling payload only, or ``None`` when unavailable.

        Returns:
            Sampling payload when available.

        """
        raw = self.raw
        if isinstance(raw, models.JobsJobResult):
            return raw.sampling
        if isinstance(raw, Mapping):
            sampling = raw.get("sampling")
            if isinstance(sampling, Mapping):
                return sampling
        return None

    def normalized_counts(self) -> dict[str, dict[int, Any]]:
        """Normalize bitstring keys into integer keys for sampling payload.

        Returns:
            Sampling counts with integer keys.

        """
        from .result_utils import normalize_sampling_result

        return normalize_sampling_result(self.sampling)

    def get_counts(self) -> dict[str, Any]:
        """Return raw counts with original bitstring keys.

        Returns:
            Raw sampling counts keyed by bitstring.

        """
        sampling = self.sampling
        if isinstance(sampling, models.JobsSamplingResult):
            return dict(sampling.counts or {})
        if isinstance(sampling, Mapping):
            counts = sampling.get("counts")
            if isinstance(counts, Mapping):
                return {str(k): v for k, v in counts.items()}
        return {}

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return f"OqtopusSamplingJobResult(job_id={self.job_id!r})"


class OqtopusEstimationJobResult(OqtopusJobResult):
    """Specialized SDK result object for estimation jobs."""

    @property
    def estimation(self) -> EstimationPayload:
        """Return estimation payload only, or ``None`` when unavailable.

        Returns:
            Estimation payload when available.

        """
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
        """Alias of :meth:`get_exp_value`.

        Returns:
            Estimated expectation value when available.

        """
        return self.get_exp_value()

    @property
    def stds(self) -> float | None:
        """Alias of :meth:`get_stds`.

        Returns:
            Estimated standard deviation when available.

        """
        return self.get_stds()

    def get_exp_value(self) -> float | None:
        """Return estimation exp_value.

        Returns:
            Estimated expectation value when available.

        """
        estimation = self.estimation
        if isinstance(estimation, models.JobsEstimationResult):
            return estimation.exp_value
        if isinstance(estimation, Mapping):
            exp_value = estimation.get("exp_value")
            return float(exp_value) if isinstance(exp_value, (int, float)) else None
        return None

    def get_stds(self) -> float | None:
        """Return estimation stds.

        Returns:
            Estimated standard deviation when available.

        """
        estimation = self.estimation
        if isinstance(estimation, models.JobsEstimationResult):
            return estimation.stds
        if isinstance(estimation, Mapping):
            stds = estimation.get("stds")
            return float(stds) if isinstance(stds, (int, float)) else None
        return None

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return f"OqtopusEstimationJobResult(job_id={self.job_id!r})"


class OqtopusMultiManualJobResult(OqtopusSamplingJobResult):
    """Specialized SDK result object for multi_manual jobs."""

    def get_divided_counts(self) -> dict[str, dict[int, Any]]:
        """Return normalized counts per sub-result from `divided_counts`.

        Returns:
            Normalized counts keyed by sub-result id.

        """
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
                {str(k): v for k, v in counts.items()},
            )
        return normalized

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
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

        Returns:
            Archive bytes in memory, or a saved file path when ``persist=True``.

        Raises:
            ValueError: If persistence arguments are inconsistent with ``persist``.

        """
        archive_bytes, default_file_name = self._get_log_archive_bytes()
        if not persist:
            if save_dir is not None or file_name is not None or overwrite:
                raise ValueError("save_dir/file_name/overwrite require persist=True.")
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
        """Decode SSE log response and return readable text.

        Returns:
            Decoded SSE log text.

        """
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
        """Read SSE log text and print it.

        Returns:
            The printed SSE log text.

        """
        text = self.read_log_text(
            encoding=encoding,
            errors=errors,
        )
        print_fn(text)
        return text

    def _require_client(self) -> OqtopusClient:
        if self._client is None:
            raise ValueError(
                "SSE log operations require a client-bound OqtopusSseJobResult."
            )
        return self._client  # type: ignore[return-value]

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return f"OqtopusSseJobResult(job_id={self.job_id!r})"
