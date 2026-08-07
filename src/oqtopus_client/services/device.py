"""Core module for oqtopus-client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from datetime import datetime

    from oqtopus_client import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusDevice:
    """Public device object wrapper."""

    raw: models.DevicesDeviceInfo

    @property
    def device_id(self) -> str:
        """Unique device identifier.

        This value is used when submitting jobs to a specific backend.

        """
        return self.raw.device_id

    @property
    def device_type(self) -> str:
        """Device type string returned by the API.

        Typical values distinguish hardware and simulator-style backends.

        """
        return self.raw.device_type

    @property
    def status(self) -> str:
        """Current availability status.

        Use this field to check whether the device is available or temporarily
        unavailable before job submission.

        """
        return self.raw.status

    @property
    def available_at(self) -> datetime | None:
        """Estimated next available time, if provided.

        This is useful when a device is busy or under maintenance and the API
        reports an expected recovery time.

        """
        return self.raw.available_at

    @property
    def n_pending_jobs(self) -> int:
        """Number of queued jobs for this device.

        This can help estimate queue pressure across multiple candidate devices.

        """
        return self.raw.n_pending_jobs

    @property
    def n_qubits(self) -> int | None:
        """Qubit count, when available.

        Some backends may omit this value when the information is not published.

        """
        return self.raw.n_qubits

    @property
    def basis_gates(self) -> list[str]:
        """Supported basis gates.

        Use this list to understand which transpiled instruction set the device
        accepts natively.

        """
        return list(self.raw.basis_gates)

    @property
    def supported_instructions(self) -> list[str]:
        """Supported instruction set names.

        These values summarize higher-level instruction families supported by
        the backend.

        """
        return list(self.raw.supported_instructions)

    @property
    def device_info(self) -> dict[str, object] | None:
        """Additional device information as a parsed dictionary.

        The API returns this field as JSON text. This property parses that
        payload into a dictionary for easier consumption.

        """
        raw_device_info = self.raw.device_info
        if not raw_device_info:
            return None

        parsed = json.loads(raw_device_info)

        if isinstance(parsed, dict):
            return cast("dict[str, object]", parsed)
        return {"value": cast("Any", parsed)}

    @property
    def calibrated_at(self) -> datetime | None:
        """Last calibration timestamp, if provided.

        This helps assess how recently the hardware calibration data was updated.

        """
        return self.raw.calibrated_at

    @property
    def description(self) -> str:
        """Human-readable device description.

        This is intended for display in UIs and logs rather than as a stable key.

        """
        return self.raw.description

    def __getattr__(self, name: str) -> object:
        """Delegate unknown attributes to the underlying generated model.

        Returns:
            The attribute value from the underlying generated model.

        """
        return getattr(self.raw, name)
