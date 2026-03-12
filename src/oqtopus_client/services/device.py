"""Core module for oqtopus-client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from oqtopus_client import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusDevice:
    """Public device object wrapper."""

    raw: models.DevicesDeviceInfo

    @property
    def device_id(self) -> str:
        """Unique device identifier."""
        return self.raw.device_id

    @property
    def device_type(self) -> str:
        """Device type string returned by API."""
        return self.raw.device_type

    @property
    def status(self) -> str:
        """Current availability status."""
        return self.raw.status

    @property
    def available_at(self) -> datetime | None:
        """Estimated next available time, if provided."""
        return self.raw.available_at

    @property
    def n_pending_jobs(self) -> int:
        """Number of queued jobs for this device."""
        return self.raw.n_pending_jobs

    @property
    def n_qubits(self) -> int | None:
        """Qubit count, when available."""
        return self.raw.n_qubits

    @property
    def basis_gates(self) -> list[str]:
        """Supported basis gates."""
        return list(self.raw.basis_gates)

    @property
    def supported_instructions(self) -> list[str]:
        """Supported instruction set names."""
        return list(self.raw.supported_instructions)

    @property
    def device_info(self) -> str | None:
        """Additional free-form device information."""
        return self.raw.device_info

    @property
    def calibrated_at(self) -> datetime | None:
        """Last calibration timestamp, if provided."""
        return self.raw.calibrated_at

    @property
    def description(self) -> str:
        """Human-readable device description."""
        return self.raw.description

    def __getattr__(self, name: str) -> object:
        """Delegate unknown attributes to the underlying generated model.

        Returns:
            The attribute value from the underlying generated model.

        """
        return getattr(self.raw, name)
