"""Core module for oqtopus-client."""

from __future__ import annotations

from dataclasses import dataclass

from oqtopus_client import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusEstimationOperator:
    """Typed operator wrapper for estimation-style job specifications."""

    pauli: str
    coeff: float | None = None

    def to_model(self) -> models.JobsOperatorItem:
        """Convert this wrapper to the REST ``JobsOperatorItem`` model.

        Returns:
            The API model for this operator.

        """
        return models.JobsOperatorItem(pauli=self.pauli, coeff=self.coeff)

    @classmethod
    def from_model(cls, operator: models.JobsOperatorItem) -> OqtopusEstimationOperator:
        """Build a wrapper from a REST ``JobsOperatorItem`` model.

        Args:
            operator (Required): REST model to convert.

        Returns:
            The converted operator wrapper.

        """
        return cls(pauli=operator.pauli, coeff=operator.coeff)
