"""Unit tests for oqtopus-client."""

from __future__ import annotations

import pytest

from oqtopus_client import (
    bitstring_dict_to_int_keys,
    bitstring_to_int,
    convert_sampling_counts_to_int_keys,
)
from oqtopus_client import rest as models


def test_bitstring_to_int_accepts_binary_and_prefixed_values() -> None:
    """Test case: test_bitstring_to_int_accepts_binary_and_prefixed_values."""
    assert bitstring_to_int("0101") == 5
    assert bitstring_to_int("0b0101") == 5
    assert bitstring_to_int(" 1_0  ") == 2


def test_bitstring_to_int_rejects_invalid_values() -> None:
    """Test case: test_bitstring_to_int_rejects_invalid_values."""
    with pytest.raises(ValueError):
        bitstring_to_int("xyz")


def test_bitstring_dict_to_int_keys_converts_mapping() -> None:
    """Test case: test_bitstring_dict_to_int_keys_converts_mapping."""
    assert bitstring_dict_to_int_keys({"00": 3, "01": 4}) == {0: 3, 1: 4}


def test_convert_sampling_counts_to_int_keys_from_model() -> None:
    """Test case: test_convert_sampling_counts_to_int_keys_from_model."""
    sampling = models.JobsSamplingResult(
        counts={"00": 8, "11": 2},
        divided_counts={"00": 0.8, "11": 0.2},
    )

    integer_key_counts = convert_sampling_counts_to_int_keys(sampling)
    assert integer_key_counts == {
        "counts": {0: 8, 3: 2},
        "divided_counts": {0: 0.8, 3: 0.2},
    }


def test_convert_sampling_counts_to_int_keys_from_mapping_and_none() -> None:
    """Test case: test_convert_sampling_counts_to_int_keys_from_mapping_and_none."""
    integer_key_counts = convert_sampling_counts_to_int_keys({"counts": {"01": 5}})
    assert integer_key_counts == {"counts": {1: 5}, "divided_counts": {}}
    assert convert_sampling_counts_to_int_keys(None) == {
        "counts": {},
        "divided_counts": {},
    }
