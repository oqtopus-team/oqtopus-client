"""Public package interface for `oqtopus_client`."""

from .client import OqtopusClient
from .config import OqtopusConfig
from .errors import ResponseValidationError, UserApiError
from .result_utils import bitstring_dict_to_int_keys, bitstring_to_int, normalize_sampling_result
from .job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from .job_spec import OqtopusJobSpec
from .estimation_operator import OqtopusEstimationOperator
from .device import OqtopusDevice
from . import rest as models

__all__ = [
    "OqtopusClient",
    "OqtopusConfig",
    "UserApiError",
    "ResponseValidationError",
    "models",
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
