from __future__ import annotations

from . import models
from .client import OqtopusClient
from .job_results import OqtopusJobResult


class OqtopusJobHandle:
    """Unified high-level wrapper for one OQTOPUS job.

    Args:
        client (Required): `OqtopusClient` used for API calls.
        job_id (Required): Target job ID.
    """

    def __init__(self, client: OqtopusClient, job_id: str) -> None:
        if not job_id:
            raise ValueError("job_id must not be empty.")
        self._client = client
        self._job_id = job_id

    @property
    def job_id(self) -> str:
        """Return job id bound to this wrapper."""
        return self._job_id

    def status(self) -> models.JobsJobStatus:
        """Get current job status."""
        return self._client.get_job_status(self.job_id).status

    def is_finished(self, *, terminal_statuses: set[models.JobsJobStatus] | None = None) -> bool:
        """Return whether the job is in terminal status.

        Args:
            terminal_statuses (Optional): Set of statuses treated as terminal.
        """
        terminal = terminal_statuses or {
            models.JobsJobStatus.SUCCEEDED,
            models.JobsJobStatus.FAILED,
            models.JobsJobStatus.CANCELLED,
        }
        return self.status() in terminal

    def wait(
        self,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
    ) -> OqtopusJobResult:
        """Wait for completion and return typed result.

        Args:
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Set of statuses treated as terminal.
            failure_statuses (Optional): Set of statuses treated as failures.
        """
        return self._client.wait_for_job(
            self.job_id,
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
        )

    def cancel(self) -> models.SuccessSuccessResponse:
        """Cancel this job."""
        return self._client.cancel_job(self.job_id)

    def refresh(self) -> OqtopusJobResult:
        """Fetch latest job result snapshot."""
        return self._client.get_job_result(self.job_id)

    def get_result(
        self,
        *,
        interval: float = 1.0,
        interval_backoff: float = 1.0,
        max_interval: float | None = None,
        timeout: float | None = 300.0,
        terminal_statuses: set[models.JobsJobStatus] | None = None,
        failure_statuses: set[models.JobsJobStatus] | None = None,
    ) -> OqtopusJobResult:
        """Wait for completion and return typed SDK result wrapper.

        Args:
            interval (Optional): Polling interval in seconds.
            interval_backoff (Optional): Backoff multiplier for polling interval.
            max_interval (Optional): Upper bound of polling interval in seconds.
            timeout (Optional): Timeout in seconds.
            terminal_statuses (Optional): Set of statuses treated as terminal.
            failure_statuses (Optional): Set of statuses treated as failures.
        """
        return self.wait(
            interval=interval,
            interval_backoff=interval_backoff,
            max_interval=max_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
            failure_statuses=failure_statuses,
        )

    def get_current_result(self) -> OqtopusJobResult:
        """Convert current job state to a typed SDK result wrapper."""
        return self.refresh()

    def __repr__(self) -> str:
        return f"OqtopusJobHandle(job_id={self.job_id!r})"
