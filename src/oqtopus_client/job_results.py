"""Compatibility re-export for `oqtopus_client.job_results`."""

from .services.job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)

__all__ = [
    "OqtopusJobResult",
    "OqtopusSamplingJobResult",
    "OqtopusEstimationJobResult",
    "OqtopusMultiManualJobResult",
    "OqtopusSseJobResult",
]
