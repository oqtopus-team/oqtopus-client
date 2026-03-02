"""Unit tests for oqtopus-client."""

from __future__ import annotations

from oqtopus_client import OqtopusEstimationOperator, OqtopusJobSpec
from oqtopus_client import rest as models


def test_estimation_operator_to_and_from_model() -> None:
    """Test case: test_estimation_operator_to_and_from_model."""
    wrapper = OqtopusEstimationOperator(pauli="Z0", coeff=1.0)
    model = wrapper.to_model()
    assert isinstance(model, models.JobsOperatorItem)
    assert model.pauli == "Z0"
    assert model.coeff == 1.0

    restored = OqtopusEstimationOperator.from_model(model)
    assert restored == wrapper


def test_estimation_operator_create_helpers() -> None:
    """Test case: test_estimation_operator_create_helpers."""
    single = OqtopusEstimationOperator.create(coeff=0.5, pauli="X 0 Z 1")
    assert single.coeff == 0.5
    assert single.pauli == "X 0 Z 1"

    many = OqtopusEstimationOperator.create_many(
        [
            (1.0, "Z 0"),
            (-0.25, "X 0 X 1"),
        ],
    )
    assert [op.coeff for op in many] == [1.0, -0.25]
    assert [op.pauli for op in many] == ["Z 0", "X 0 X 1"]


def test_job_spec_estimation_accepts_operator_wrapper() -> None:
    """Test case: test_job_spec_estimation_accepts_operator_wrapper."""
    spec = OqtopusJobSpec.estimation(
        device_id="Kawasaki",
        program="OPENQASM 3; qubit[1] q;",
        operator=[OqtopusEstimationOperator(pauli="Z0", coeff=1)],
    )
    submit = spec.to_submit_job_request()
    assert submit.job_info.operator is not None
    assert submit.job_info.operator[0].pauli == "Z0"
    assert submit.job_info.operator[0].coeff == 1
