"""SSE runtime payload example for VQE-style estimation loops."""

from __future__ import annotations

import math

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusEstimationOperator,
    OqtopusJobSpec,
)


def _build_program(theta: float) -> str:
    return f"""OPENQASM 3;
include \"stdgates.inc\";
qubit[2] q;
bit[2] c;

ry({theta}) q[0];
cx q[0], q[1];
c = measure q;
"""


def main() -> None:
    """Run a simple VQE-style loop from SSE runtime and print the best point."""
    # In SSE runtime, use base_url="" and device_id="sse".
    client = OqtopusClient(OqtopusConfig(base_url=""))

    n_grid = 5
    theta_values = [2.0 * math.pi * i / (n_grid - 1) for i in range(n_grid)]
    best_theta = 0.0
    best_energy = float("inf")

    for i, theta in enumerate(theta_values):
        result = client.run_estimation(
            OqtopusJobSpec.estimation(
                name=f"SSE Runtime VQE step {i}",
                description="scan a single RY parameter for <X0X1> + <Z0Z1>",
                device_id="sse",
                shots=1000,
                program=_build_program(theta),
                operator=[
                    OqtopusEstimationOperator(pauli="X 0 X 1", coeff=1.0),
                    OqtopusEstimationOperator(pauli="Z 0 Z 1", coeff=1.0),
                ],
            ),
            timeout=120.0,
        )

        if result is None or result.exp_value is None:
            print(f"Step {i}: No result received.")
            continue

        energy = float(result.exp_value)
        if energy < best_energy:
            best_energy = energy
            best_theta = theta

        print(
            {
                "step": i,
                "job_id": result.job_id,
                "theta": theta,
                "energy": energy,
                "stds": result.stds,
            }
        )

    print({"best_theta": best_theta, "best_energy": best_energy})


if __name__ == "__main__":
    main()
