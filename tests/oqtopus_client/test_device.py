"""Unit tests for oqtopus-client."""

from __future__ import annotations

import json

import pytest

from oqtopus_client import OqtopusDevice
from oqtopus_client import rest as models


def test_device_wrapper_exposes_properties_and_raw_attributes() -> None:
    """Test case: test_device_wrapper_exposes_properties_and_raw_attributes."""
    device = OqtopusDevice(
        raw=models.DevicesDeviceInfo(
            device_id="K",
            device_type="simulator",
            status="available",
            available_at=None,
            n_pending_jobs=0,
            n_qubits=2,
            basis_gates=["x", "h"],
            supported_instructions=["measure"],
            device_info='{"backend":"sim"}',
            calibrated_at=None,
            description="sim",
        ),
    )
    assert device.device_id == "K"
    assert device.device_type == "simulator"
    assert device.status == "available"
    assert device.available_at is None
    assert device.n_pending_jobs == 0
    assert device.n_qubits == 2
    assert device.basis_gates == ["x", "h"]
    assert device.supported_instructions == ["measure"]
    assert device.device_info == {"backend": "sim"}
    assert device.calibrated_at is None
    assert device.description == "sim"


def test_device_info_raises_for_malformed_json() -> None:
    """Test case: test_device_info_raises_for_malformed_json."""
    device = OqtopusDevice(
        raw=models.DevicesDeviceInfo(
            device_id="K",
            device_type="simulator",
            status="available",
            available_at=None,
            n_pending_jobs=0,
            n_qubits=2,
            basis_gates=["x", "h"],
            supported_instructions=["measure"],
            device_info="not-json",
            calibrated_at=None,
            description="sim",
        ),
    )

    with pytest.raises(json.JSONDecodeError):
        _ = device.device_info


@pytest.mark.parametrize("raw_device_info", [None, ""])
def test_device_info_is_none_for_missing_payload(
    raw_device_info: str | None,
) -> None:
    """Test case: test_device_info_is_none_for_missing_payload."""
    device = OqtopusDevice(
        raw=models.DevicesDeviceInfo(
            device_id="K",
            device_type="simulator",
            status="available",
            available_at=None,
            n_pending_jobs=0,
            n_qubits=2,
            basis_gates=["x", "h"],
            supported_instructions=["measure"],
            device_info=raw_device_info,
            calibrated_at=None,
            description="sim",
        ),
    )

    assert device.device_info is None
