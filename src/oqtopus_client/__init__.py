"""Public package interface for `oqtopus_client`."""

from . import rest
from .services.client import OqtopusClient
from .services.config import OqtopusConfig
from .services.device import OqtopusDevice
from .services.errors import ResponseValidationError, UserApiError
from .services.estimation_operator import OqtopusEstimationOperator
from .services.job_results import (
    OqtopusEstimationJobResult,
    OqtopusJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from .services.job_spec import OqtopusJobSpec
from .services.result_utils import (
    bitstring_dict_to_int_keys,
    bitstring_to_int,
    convert_sampling_counts_to_int_keys,
)

__all__ = [
    "OqtopusClient",
    "OqtopusConfig",
    "OqtopusDevice",
    "OqtopusEstimationJobResult",
    "OqtopusEstimationOperator",
    "OqtopusJobResult",
    "OqtopusJobSpec",
    "OqtopusMultiManualJobResult",
    "OqtopusSamplingJobResult",
    "OqtopusSseJobResult",
    "ResponseValidationError",
    "UserApiError",
    "bitstring_dict_to_int_keys",
    "bitstring_to_int",
    "convert_sampling_counts_to_int_keys",
    "rest",
]
