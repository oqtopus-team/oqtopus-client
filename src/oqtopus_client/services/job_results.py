"""Core module for oqtopus-client."""

from __future__ import annotations

import base64
import binascii
import io
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from oqtopus_client import rest as models
from oqtopus_client.services.result_utils import (
    bitstring_dict_to_int_keys,
    convert_sampling_counts_to_int_keys,
)

if TYPE_CHECKING:
    from datetime import datetime

    from typing_extensions import Self

    from .client import OqtopusClient

SamplingPayload: TypeAlias = models.JobsS3SamplingResult | Mapping[str, Any] | None
EstimationPayload: TypeAlias = (
    models.JobsS3EstimationResult | Mapping[str, Any] | None
)


def _mapping_like_to_dict(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return cast("dict[str, Any]", value.to_dict())
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return cast("dict[str, Any]", value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _with_legacy_job_info_aliases(job_info: dict[str, Any]) -> dict[str, Any]:
    compat = dict(job_info)
    input_payload = _mapping_like_to_dict(compat.get("input"))
    if input_payload is None:
        return compat

    if "program" not in compat and "program" in input_payload:
        compat["program"] = input_payload["program"]
    if "operator" not in compat and "operator" in input_payload:
        compat["operator"] = input_payload["operator"]

    return compat


class _CompatJobsJobInfo(models.JobsJobInfo):
    def to_dict(self) -> dict[str, Any]:
        compat = _with_legacy_job_info_aliases(super().to_dict())
        compat.setdefault("message", self.message)
        return compat


def _wrap_job_info(
    job_info: models.JobsJobInfo | Mapping[str, Any] | None,
) -> models.JobsJobInfo | Mapping[str, Any] | None:
    if job_info is None:
        return None
    if isinstance(job_info, _CompatJobsJobInfo):
        return job_info
    if isinstance(job_info, models.JobsJobInfo):
        return _CompatJobsJobInfo(
            input=job_info.input,
            combined_program=job_info.combined_program,
            result=job_info.result,
            transpile_result=job_info.transpile_result,
            sse_log=job_info.sse_log,
            message=job_info.message,
        )
    if isinstance(job_info, Mapping):
        return _with_legacy_job_info_aliases(dict(job_info))
    return job_info


class OqtopusJobResult:  # noqa: PLR0904
    """SDK result object for a job's state and execution output payloads."""

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
    _transpile_result: (
        models.JobsS3TranspileResult | Mapping[str, Any] | None
    )
    _message: str | None
    _execution_time: float | None
    _submitted_at: datetime | None
    _ready_at: datetime | None
    _running_at: datetime | None
    _ended_at: datetime | None
    _client: object | None

    def __init__(  # noqa: PLR0913
        self,
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
        transpile_result: (
            models.JobsS3TranspileResult | Mapping[str, Any] | None
        ) = None,
        message: str | None = None,
        execution_time: float | None = None,
        submitted_at: datetime | None = None,
        ready_at: datetime | None = None,
        running_at: datetime | None = None,
        ended_at: datetime | None = None,
        client: object | None = None,
    ) -> None:
        """Initialize a job result wrapper from job metadata and execution payload.

        Raises:
            ValueError: If ``job_type`` or ``status`` is invalid.

        """
        self._job_id = job_id
        self._job_type = self._coerce_job_type(job_type)
        self._status = self._coerce_status(status)
        self._name = name
        self._description = description
        self._device_id = device_id
        self._shots = shots
        self._job_info = _wrap_job_info(job_info)
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
            msg = f"Invalid job_type: {job_type!r}"
            raise ValueError(msg)
        if self._status is None:
            msg = f"Invalid status: {status!r}"
            raise ValueError(msg)

    @classmethod
    def from_raw(
        cls,
        job: models.JobsJob,
        *,
        client: object | None = None,
    ) -> Self:
        """Build a result object from a full job payload.

        Args:
            job (Required): Job definition returned by the API.
            client (Optional): Client object bound to this result.

        Returns:
            A result object populated from the job definition.

        Raises:
            ValueError: If the payload is missing required submitted-job fields.

        """
        required = {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "name": job.name,
            "device_id": job.device_id,
            "shots": job.shots,
            "job_info": job.job_info,
        }
        missing = [key for key, value in required.items() if value is None]
        if missing:
            msg = f"Job payload is missing required fields: {', '.join(missing)}"
            raise ValueError(msg)

        job_info = job.job_info
        transpile_result = job_info.transpile_result if job_info is not None else None
        message = job_info.message if job_info is not None else None
        return cls(
            job_id=cast("str", job.job_id),
            job_type=cast("models.JobsJobType | str", job.job_type),
            status=cast("models.JobsJobStatus | str", job.status),
            name=cast("str", job.name),
            description=job.description,
            device_id=cast("str", job.device_id),
            shots=cast("int", job.shots),
            job_info=cast("models.JobsJobInfo | Mapping[str, Any]", job.job_info),
            transpiler_info=job.transpiler_info,
            simulator_info=job.simulator_info,
            mitigation_info=job.mitigation_info,
            transpile_result=transpile_result,
            message=message,
            execution_time=job.execution_time,
            submitted_at=job.submitted_at,
            ready_at=job.ready_at,
            running_at=job.running_at,
            ended_at=job.ended_at,
            client=client,
        )

    @property
    def job_id(self) -> str | None:
        """Return the related job id when known.

        This is the same identifier used by client methods such as ``status()``,
        ``wait()``, and ``cancel_job()``.

        """
        return self._job_id

    @property
    def job_type(self) -> models.JobsJobType | None:
        """Return the related job type when known.

        Examples include ``sampling``, ``estimation``, ``multi_manual``, and
        ``sse``.

        """
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
        """Return the related job name when known.

        This corresponds to the optional name supplied when the job was
        submitted.

        """
        return self._name

    @property
    def description(self) -> str | None:
        """Return the related job description when known.

        This corresponds to the optional description supplied at submission time.

        """
        return self._description

    @property
    def device_id(self) -> str | None:
        """Return the related device id when known.

        This identifies the backend where the job was submitted.

        """
        return self._device_id

    @property
    def shots(self) -> int | None:
        """Return the related shot count when known.

        For job types that do not use sampling-style shots, this may be absent.

        """
        return self._shots

    @property
    def job_info(self) -> models.JobsJobInfo | Mapping[str, Any] | None:
        """Return the related ``job_info`` payload when known.

        This contains nested execution results and other API-provided metadata.

        """
        return _wrap_job_info(self._job_info)

    @property
    def transpiler_info(self) -> Mapping[str, Any] | None:
        """Return the related transpiler info when known.

        This is the transpiler metadata submitted with the job or echoed back by
        the API.

        """
        return self._transpiler_info

    @property
    def simulator_info(self) -> Mapping[str, Any] | None:
        """Return the related simulator info when known.

        This is typically present for simulator-backed executions.

        """
        return self._simulator_info

    @property
    def mitigation_info(self) -> Mapping[str, Any] | None:
        """Return the related mitigation info when known.

        This contains error-mitigation settings associated with the job.

        """
        return self._mitigation_info

    @property
    def transpile_result(
        self,
    ) -> models.JobsS3TranspileResult | Mapping[str, Any] | None:
        """Return the related transpile result when known.

        This may include transpiled circuits or backend-specific transpilation
        metadata returned by the API.

        """
        return self._transpile_result

    @property
    def message(self) -> str | None:
        """Return the related message when known.

        Error details and backend-provided status messages are often surfaced
        here.

        """
        return self._message

    @property
    def execution_time(self) -> float | int | None:
        """Return the related execution time in seconds when known.

        This value is reported by the API and may be absent for unfinished jobs.

        """
        return self._execution_time

    @property
    def submitted_at(self) -> datetime | None:
        """Return the related submission time when known.

        This timestamp is set when the API accepts the job.

        """
        return self._submitted_at

    @property
    def ready_at(self) -> datetime | None:
        """Return the related ready time when known.

        This timestamp is set when the job has been prepared and is ready to run.

        """
        return self._ready_at

    @property
    def running_at(self) -> datetime | None:
        """Return the related running time when known.

        This timestamp is set when execution actually starts.

        """
        return self._running_at

    @property
    def ended_at(self) -> datetime | None:
        """Return the related end time when known.

        This timestamp is set when the job reaches a terminal state.

        """
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
    def _coerce_job_type(
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
    def _coerce_status(
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

    @staticmethod
    def _extract_branch(
        result: object,
        key: str,
    ) -> (
        models.JobsS3SamplingResult
        | models.JobsS3EstimationResult
        | Mapping[str, Any]
        | None
    ):
        if isinstance(result, models.JobsS3JobResult):
            return cast(
                "models.JobsS3SamplingResult | models.JobsS3EstimationResult | None",
                getattr(result, key),
            )
        if isinstance(result, Mapping):
            branch = result.get(key)
            if isinstance(
                branch,
                (Mapping, models.JobsS3SamplingResult, models.JobsS3EstimationResult),
            ):
                return branch
        return None

    @property
    def sampling(self) -> SamplingPayload:
        """Return sampling payload when result is sampling-like.

        Returns:
            Sampling payload when available.

        """
        job_info = self.job_info
        if isinstance(job_info, models.JobsJobInfo):
            return cast(
                "SamplingPayload",
                self._extract_branch(job_info.result, "sampling"),
            )
        if isinstance(job_info, Mapping):
            return cast(
                "SamplingPayload",
                self._extract_branch(job_info.get("result"), "sampling"),
            )
        return None

    @property
    def estimation(self) -> EstimationPayload:
        """Return estimation payload when result is estimation-like.

        Returns:
            Estimation payload when available.

        """
        job_info = self.job_info
        if isinstance(job_info, models.JobsJobInfo):
            return cast(
                "EstimationPayload",
                self._extract_branch(job_info.result, "estimation"),
            )
        if isinstance(job_info, Mapping):
            return cast(
                "EstimationPayload",
                self._extract_branch(job_info.get("result"), "estimation"),
            )
        return None


class OqtopusSamplingJobResult(OqtopusJobResult):
    """Specialized SDK result object for sampling jobs."""

    @property
    def sampling(self) -> SamplingPayload:
        """Return sampling payload only, or ``None`` when unavailable.

        Returns:
            Sampling payload when available.

        """
        return super().sampling

    def counts_with_integer_keys(self) -> dict[str, dict[int, Any]]:
        """Convert bitstring keys to integer keys for sampling payload.

        Returns:
            Sampling counts with integer keys.

        """
        return convert_sampling_counts_to_int_keys(self.sampling)

    def get_counts(self) -> dict[str, Any]:
        """Return raw counts with original bitstring keys.

        Returns:
            Raw sampling counts keyed by bitstring.

        """
        sampling = self.sampling
        if isinstance(sampling, models.JobsS3SamplingResult):
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
        return super().estimation

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
        if isinstance(estimation, models.JobsS3EstimationResult):
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
        if isinstance(estimation, models.JobsS3EstimationResult):
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
        """Return integer-keyed counts per sub-result from `divided_counts`.

        Returns:
            Integer-keyed counts keyed by sub-result id.

        """
        sampling = self.sampling
        if isinstance(sampling, models.JobsS3SamplingResult):
            divided_counts = sampling.divided_counts
        elif isinstance(sampling, Mapping):
            divided_counts = sampling.get("divided_counts")
        else:
            divided_counts = None

        if not isinstance(divided_counts, Mapping):
            return {}

        integer_key_counts: dict[str, dict[int, Any]] = {}
        for result_key, counts in divided_counts.items():
            if not isinstance(counts, Mapping):
                continue
            integer_key_counts[str(result_key)] = bitstring_dict_to_int_keys(
                {str(k): v for k, v in counts.items()},
            )
        return integer_key_counts

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return f"OqtopusMultiManualJobResult(job_id={self.job_id!r})"


class OqtopusSseJobResult(OqtopusJobResult):
    """Specialized SDK result object for sse jobs."""

    def _to_jobs_job(self) -> models.JobsJob:
        if self.job_info is None:
            job_info = None
        elif isinstance(self.job_info, models.JobsJobInfo):
            job_info = self.job_info
        elif isinstance(self.job_info, Mapping):
            job_info = models.JobsJobInfo.from_dict(
                _mapping_like_to_dict(self.job_info)
            )

        return models.JobsJob(
            job_id=self.job_id,
            job_type=self.job_type,
            status=self.status,
            name=self.name,
            description=self.description,
            device_id=self.device_id,
            shots=self.shots,
            job_info=job_info,
            transpiler_info=_mapping_like_to_dict(self.transpiler_info),
            simulator_info=_mapping_like_to_dict(self.simulator_info),
            mitigation_info=_mapping_like_to_dict(self.mitigation_info),
            execution_time=self.execution_time,
            submitted_at=self.submitted_at,
            ready_at=self.ready_at,
            running_at=self.running_at,
            ended_at=self.ended_at,
        )

    def get_job_result(self) -> (
            OqtopusSamplingJobResult
            | OqtopusEstimationJobResult
            | OqtopusMultiManualJobResult
            | OqtopusJobResult
    ):
        """Return a job result object with the specific type based on available payload.

        Returns:
            A job result object with the specific type based on available payload.

        """
        job = self._to_jobs_job()
        sampling = self.sampling
        if sampling is not None:
            if isinstance(sampling, models.JobsS3SamplingResult):
                is_multi_manual = sampling.divided_counts is not None
            elif isinstance(sampling, Mapping):
                is_multi_manual = sampling.get("divided_counts") is not None
            else:
                is_multi_manual = False

            if is_multi_manual:
                return OqtopusMultiManualJobResult.from_raw(
                    job=job,
                    client=self._client
                )
            return OqtopusSamplingJobResult.from_raw(job=job, client=self._client)

        if self.estimation is not None:
            return OqtopusEstimationJobResult.from_raw(job=job, client=self._client)

        return OqtopusJobResult.from_raw(job=job, client=self._client)

    def _get_log_archive_bytes(self) -> tuple[bytes, str]:
        client = self._require_client()
        if self.job_id is None:
            msg = "job_id is required for SSE log operations."
            raise ValueError(msg)
        response = client.get_sselog(self.job_id)
        if response.file is None or response.file_name is None:
            msg = "SSE log response does not contain valid file data."
            raise ValueError(msg)
        try:
            decoded = base64.b64decode(response.file, validate=True)
        except binascii.Error as e:
            msg = "SSE log file field is not valid base64 data."
            raise ValueError(msg) from e
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
            msg = f"The destination path does not exist: {out_dir}"
            raise ValueError(msg)
        if not out_dir.is_dir():
            msg = f"The destination path is not a directory: {out_dir}"
            raise ValueError(msg)

        out_path = out_dir / file_name
        if out_path.exists() and not overwrite:
            msg = f"The file already exists: {out_path}"
            raise ValueError(msg)
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

        Args:
            save_dir (Optional): Destination directory used when ``persist=True``.
            file_name (Optional): Saved archive file name when ``persist=True``.
            overwrite (Optional): Whether to overwrite an existing file when
                ``persist=True``.
            persist (Optional): Whether to save the archive to disk instead of
                returning bytes.

        Returns:
            Archive bytes in memory, or a saved file path when ``persist=True``.

        Raises:
            ValueError: If persistence arguments are inconsistent with ``persist``.

        """
        archive_bytes, default_file_name = self._get_log_archive_bytes()
        if not persist:
            if save_dir is not None or file_name is not None or overwrite:
                msg = "save_dir/file_name/overwrite require persist=True."
                raise ValueError(msg)
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

        Args:
            encoding (Optional): Text encoding used to decode log contents.
            errors (Optional): Error handling mode passed to ``decode()``.

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

        Args:
            encoding (Optional): Text encoding used to decode log contents.
            errors (Optional): Error handling mode passed to ``decode()``.
            print_fn (Optional): Printer function used to display the decoded log.

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
            msg = "SSE log operations require a client-bound OqtopusSseJobResult."
            raise ValueError(msg)
        return self._client  # type: ignore[return-value]

    def __repr__(self) -> str:
        """Return a concise debug representation.

        Returns:
            A debug-friendly string representation.

        """
        return f"OqtopusSseJobResult(job_id={self.job_id!r})"
