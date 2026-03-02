"""Core module for oqtopus-client."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .. import rest as models


@dataclass(frozen=True, slots=True)
class OqtopusEstimationOperator:
    """Typed operator wrapper for estimation-style job specifications."""

    pauli: str
    coeff: float | int | None = None

    @classmethod
    def create(
        cls,
        *,
        coeff: float | None,
        pauli: str,
    ) -> OqtopusEstimationOperator:
        """Create one operator term from explicit ``coeff`` and ``pauli``."""
        return cls(pauli=pauli, coeff=coeff)

    @classmethod
    def create_many(
        cls,
        terms: Sequence[tuple[float | int | None, str]],
    ) -> list[OqtopusEstimationOperator]:
        """Create multiple operator terms from ``(coeff, pauli)`` tuples."""
        return [cls(coeff=coeff, pauli=pauli) for coeff, pauli in terms]

    def to_model(self) -> models.JobsOperatorItem:
        """Convert this wrapper to the generated ``JobsOperatorItem`` model."""
        return models.JobsOperatorItem(pauli=self.pauli, coeff=self.coeff)

    @classmethod
    def from_model(cls, operator: models.JobsOperatorItem) -> OqtopusEstimationOperator:
        """Build a wrapper from a generated ``JobsOperatorItem`` model."""
        return cls(pauli=operator.pauli, coeff=operator.coeff)
