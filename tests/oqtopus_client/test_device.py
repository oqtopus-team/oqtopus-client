"""Unit tests for oqtopus-client."""

from __future__ import annotations

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
