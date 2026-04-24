"""Core module for oqtopus-client."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from oqtopus_client import rest as models
from oqtopus_client.services.estimation_operator import OqtopusEstimationOperator

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def _as_program_list(program: str | Sequence[str]) -> list[str]:
    if isinstance(program, str):
        return [program]
    return list(program)


def _encode_programs_base64(program: str | Sequence[str]) -> list[str]:
    return [
        base64.b64encode(text.encode("utf-8")).decode("utf-8")
        for text in _as_program_list(program)
    ]


def _coerce_operators(
    operator: Sequence[
        OqtopusEstimationOperator | models.JobsS3OperatorItem | Mapping[str, Any]
    ]
    | None,
) -> list[models.JobsS3OperatorItem] | None:
    if operator is None:
        return None
    coerced: list[models.JobsS3OperatorItem] = []
    for item in operator:
        if isinstance(item, OqtopusEstimationOperator):
            coerced.append(item.to_model())
        elif isinstance(item, models.JobsS3OperatorItem):
            coerced.append(item)
        else:
            coerced.append(models.JobsS3OperatorItem.model_validate(dict(item)))
    return coerced


@dataclass(slots=True)
class OqtopusJobSpec:
    """Thin wrapper input for job submission.

    Use ``job_type`` to choose the execution type (e.g. ``sampling`` / ``estimation``).

    Attributes:
        device_id (Required): Target device ID.
        job_type (Required): Job type.
        program (Required): One program string or a sequence of program strings.
        shots (Optional): Number of shots. Default is ``1000``.
        name (Optional): Job name.
        description (Optional): Job description.
        transpiler_info (Optional): Transpiler settings.
        simulator_info (Optional): Simulator settings.
        mitigation_info (Optional): Error mitigation settings.
        operator (Optional): Operator definitions for estimation-style jobs.

    """

    device_id: str
    job_type: models.JobsJobType | str
    program: str | Sequence[str]
    shots: int = 1000
    name: str | None = None
    description: str | None = None
    transpiler_info: Mapping[str, Any] = field(default_factory=dict)
    simulator_info: Mapping[str, Any] = field(default_factory=dict)
    mitigation_info: Mapping[str, Any] = field(default_factory=dict)
    operator: (
        Sequence[
            OqtopusEstimationOperator | models.JobsS3OperatorItem | Mapping[str, Any]
        ]
        | None
    ) = None

    @classmethod
    def sampling(  # noqa: PLR0913
        cls,
        *,
        device_id: str,
        program: str | Sequence[str],
        shots: int = 1000,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
        operator: Sequence[
            OqtopusEstimationOperator | models.JobsS3OperatorItem | Mapping[str, Any]
        ]
        | None = None,
    ) -> OqtopusJobSpec:
        """Create a sampling job request helper.

        Args:
            device_id (Required): Target device ID.
            program (Required): A QASM string or a sequence of QASM strings.
            shots (Optional): Number of shots. Default is ``1000``.
            name (Optional): Job name.
            description (Optional): Job description.
            transpiler_info (Optional): Transpiler settings.
            simulator_info (Optional): Simulator settings.
            mitigation_info (Optional): Error mitigation settings.
            operator (Optional): Operator definitions.

        Returns:
            A sampling job specification.

        """
        return cls(
            device_id=device_id,
            job_type=models.JobsJobType.SAMPLING,
            program=program,
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            operator=operator,
        )

    @classmethod
    def estimation(  # noqa: PLR0913
        cls,
        *,
        device_id: str,
        program: str | Sequence[str],
        shots: int = 1000,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
        operator: Sequence[
            OqtopusEstimationOperator | models.JobsS3OperatorItem | Mapping[str, Any]
        ]
        | None = None,
    ) -> OqtopusJobSpec:
        """Create an estimation job request helper.

        Args:
            device_id (Required): Target device ID.
            program (Required): A QASM string or a sequence of QASM strings.
            shots (Optional): Number of shots. Default is ``1000``.
            name (Optional): Job name.
            description (Optional): Job description.
            transpiler_info (Optional): Transpiler settings.
            simulator_info (Optional): Simulator settings.
            mitigation_info (Optional): Error mitigation settings.
            operator (Optional): Operator definitions.

        Returns:
            An estimation job specification.

        """
        return cls(
            device_id=device_id,
            job_type=models.JobsJobType.ESTIMATION,
            program=program,
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            operator=operator,
        )

    @classmethod
    def multi_manual(  # noqa: PLR0913
        cls,
        *,
        device_id: str,
        program: str | Sequence[str],
        shots: int = 1000,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
        operator: Sequence[
            OqtopusEstimationOperator | models.JobsS3OperatorItem | Mapping[str, Any]
        ]
        | None = None,
    ) -> OqtopusJobSpec:
        """Create a multi-manual job request helper.

        Args:
            device_id (Required): Target device ID.
            program (Required): A QASM string or a sequence of QASM strings.
            shots (Optional): Number of shots. Default is ``1000``.
            name (Optional): Job name.
            description (Optional): Job description.
            transpiler_info (Optional): Transpiler settings.
            simulator_info (Optional): Simulator settings.
            mitigation_info (Optional): Error mitigation settings.
            operator (Optional): Operator definitions.

        Returns:
            A multi-manual job specification.

        """
        return cls(
            device_id=device_id,
            job_type=models.JobsJobType.MULTI_MANUAL,
            program=program,
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            operator=operator,
        )

    @classmethod
    def sse(  # noqa: PLR0913
        cls,
        *,
        device_id: str,
        program: str | Sequence[str],
        shots: int = 1000,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: Mapping[str, Any] | None = None,
        simulator_info: Mapping[str, Any] | None = None,
        mitigation_info: Mapping[str, Any] | None = None,
    ) -> OqtopusJobSpec:
        """Create an SSE job request helper.

        Args:
            device_id (Required): Target device ID.
            program (Required): A Python script string or a sequence of script strings.
                Each entry is UTF-8/base64-encoded automatically for API submission.
            shots (Optional): Number of shots. Default is ``1000``.
            name (Optional): Job name.
            description (Optional): Job description.
            transpiler_info (Optional): Transpiler settings.
            simulator_info (Optional): Simulator settings.
            mitigation_info (Optional): Error mitigation settings.

        Returns:
            An SSE job specification.

        """
        return cls(
            device_id=device_id,
            job_type=models.JobsJobType.SSE,
            program=_encode_programs_base64(program),
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info or {},
            simulator_info=simulator_info or {},
            mitigation_info=mitigation_info or {},
            operator=None,
        )

    def to_model(self) -> models.JobsSubmitJobRequest:
        """Convert to the generated ``JobsSubmitJobRequest`` model.

        This method has no arguments. It converts required/optional fields
        already set on this instance.

        Returns:
            The generated job submission request model.

        """
        job_type = self.job_type
        if isinstance(job_type, str):
            job_type = models.JobsJobType(job_type)
        return models.JobsSubmitJobRequest(
            name=self.name,
            description=self.description,
            device_id=self.device_id,
            job_type=job_type,
            shots=self.shots,
            transpiler_info=dict(self.transpiler_info or {}),
            simulator_info=dict(self.simulator_info or {}),
            mitigation_info=dict(self.mitigation_info or {}),
        )

    def to_s3_submit_job_info(self) -> models.JobsS3SubmitJobInfo:
        """Convert to the generated ``JobsS3SubmitJobInfo`` model.

        Returns:
            The generated S3 offload payload model.

        """
        return models.JobsS3SubmitJobInfo(
            program=_as_program_list(self.program),
            operator=_coerce_operators(self.operator),
        )
