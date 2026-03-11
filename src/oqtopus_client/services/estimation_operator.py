"""Core module for oqtopus-client."""

from __future__ import annotations

from dataclasses import dataclass

from .. import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusEstimationOperator:
    """Typed operator wrapper for estimation-style job specifications."""

    pauli: str
    coeff: float | None = None

    def to_model(self) -> models.JobsOperatorItem:
        """Convert this wrapper to the generated ``JobsOperatorItem`` model.

        Returns:
            The generated API model for this operator.

        """
        return models.JobsOperatorItem(pauli=self.pauli, coeff=self.coeff)

    @classmethod
    def from_model(cls, operator: models.JobsOperatorItem) -> OqtopusEstimationOperator:
        """Build a wrapper from a generated ``JobsOperatorItem`` model.

        Returns:
            The converted operator wrapper.

        """
        return cls(pauli=operator.pauli, coeff=operator.coeff)
