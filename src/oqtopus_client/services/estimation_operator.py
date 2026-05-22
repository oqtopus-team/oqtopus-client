"""Core module for oqtopus-client."""

from __future__ import annotations

from dataclasses import dataclass

from oqtopus_client import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusEstimationOperator:
    """Typed operator wrapper for estimation-style job specifications."""

    pauli: str
    coeff: float | None = None

    def to_model(self) -> models.JobsS3OperatorItem:
        """Convert this wrapper to the REST ``JobsS3OperatorItem`` model.

        Returns:
            The API model for this operator.

        """
        return models.JobsS3OperatorItem(pauli=self.pauli, coeff=self.coeff)

    @classmethod
    def from_model(
        cls,
        operator: models.JobsS3OperatorItem,
    ) -> OqtopusEstimationOperator:
        """Build a wrapper from a REST ``JobsS3OperatorItem`` model.

        Args:
            operator (Required): REST model to convert.

        Returns:
            The converted operator wrapper.

        """
        return cls(pauli=operator.pauli, coeff=operator.coeff)
