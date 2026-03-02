"""Compatibility re-export for `oqtopus_client.result_utils`."""

from .services.result_utils import bitstring_dict_to_int_keys, bitstring_to_int, normalize_sampling_result

__all__ = ["bitstring_to_int", "bitstring_dict_to_int_keys", "normalize_sampling_result"]
