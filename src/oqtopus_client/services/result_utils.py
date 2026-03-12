"""Core module for oqtopus-client."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from oqtopus_client import rest as models

if TYPE_CHECKING:
    from collections.abc import Mapping


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
        msg = f"Invalid bitstring: {bitstring!r}"
        raise ValueError(msg)
    return int(normalized, 2)


def bitstring_dict_to_int_keys(
    values: Mapping[str, object] | None,
) -> dict[int, object]:
    """Convert bitstring-keyed mappings to int-keyed mappings.

    Returns:
        A mapping with integer keys.

    """
    if not values:
        return {}
    return {bitstring_to_int(key): value for key, value in values.items()}


def normalize_sampling_result(
    sampling_result: models.JobsSamplingResult | Mapping[str, object] | None,
) -> dict[str, dict[int, object]]:
    """Normalize sampling result counts by converting bitstring keys to integers.

    Returns:
        Normalized ``counts`` and ``divided_counts`` dictionaries.

    """
    if sampling_result is None:
        return {"counts": {}, "divided_counts": {}}

    counts: Mapping[str, object] | None
    divided_counts: Mapping[str, object] | None
    if isinstance(sampling_result, models.JobsSamplingResult):
        counts = sampling_result.counts
        divided_counts = sampling_result.divided_counts
    else:
        counts = cast("Mapping[str, object] | None", sampling_result.get("counts"))
        divided_counts = cast(
            "Mapping[str, object] | None",
            sampling_result.get("divided_counts"),
        )

    return {
        "counts": bitstring_dict_to_int_keys(counts),
        "divided_counts": bitstring_dict_to_int_keys(divided_counts),
    }
