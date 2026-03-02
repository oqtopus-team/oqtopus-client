"""Public package interface for `oqtopus_client`."""

from . import rest
from .services.client import OqtopusClient
from .services.config import OqtopusConfig
from .services.errors import ResponseValidationError, UserApiError
from .services.result_utils import bitstring_dict_to_int_keys, bitstring_to_int, normalize_sampling_result
from .services.job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from .services.job_spec import OqtopusJobSpec
from .services.estimation_operator import OqtopusEstimationOperator
from .services.device import OqtopusDevice

__all__ = [
    "OqtopusClient",
    "OqtopusConfig",
    "UserApiError",
    "ResponseValidationError",
    "rest",
    "bitstring_to_int",
    "bitstring_dict_to_int_keys",
    "normalize_sampling_result",
    "OqtopusJobResult",
    "OqtopusSamplingJobResult",
    "OqtopusEstimationJobResult",
    "OqtopusMultiManualJobResult",
    "OqtopusSseJobResult",
    "OqtopusJobSpec",
    "OqtopusEstimationOperator",
    "OqtopusDevice",
]
