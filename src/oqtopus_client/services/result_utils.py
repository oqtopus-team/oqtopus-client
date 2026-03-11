"""Core module for oqtopus-client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import rest as models


def bitstring_to_int(bitstring: str) -> int:
    """Convert a bitstring key such as `0101` or `0b0101` to an integer.

    Returns:
        The integer value of the normalized bitstring.

    Raises:
        ValueError: If ``bitstring`` is not a valid binary string.

    """
    normalized = bitstring.strip().replace("_", "").replace(" ", "")
    normalized = normalized.removeprefix("0b")
    if not normalized or any(char not in {"0", "1"} for char in normalized):
        raise ValueError(f"Invalid bitstring: {bitstring!r}")
    return int(normalized, 2)


def bitstring_dict_to_int_keys(values: Mapping[str, Any] | None) -> dict[int, Any]:
    """Convert bitstring-keyed mappings to int-keyed mappings.

    Returns:
        A mapping with integer keys.

    """
    if not values:
        return {}
    return {bitstring_to_int(key): value for key, value in values.items()}


def normalize_sampling_result(
    sampling_result: models.JobsSamplingResult | Mapping[str, Any] | None,
) -> dict[str, dict[int, Any]]:
    """Normalize sampling result counts by converting bitstring keys to integers.

    Returns:
        Normalized ``counts`` and ``divided_counts`` dictionaries.

    """
    if sampling_result is None:
        return {"counts": {}, "divided_counts": {}}

    if isinstance(sampling_result, models.JobsSamplingResult):
        counts = sampling_result.counts
        divided_counts = sampling_result.divided_counts
    else:
        counts = sampling_result.get("counts")
        divided_counts = sampling_result.get("divided_counts")

    return {
        "counts": bitstring_dict_to_int_keys(counts),
        "divided_counts": bitstring_dict_to_int_keys(divided_counts),
    }
