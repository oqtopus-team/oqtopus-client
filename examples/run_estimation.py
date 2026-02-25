from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusEstimationOperator,
    OqtopusJobSpec,
)

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

program = """OPENQASM 3;
include \"stdgates.inc\";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

req = OqtopusJobSpec.estimation(
    name="Bell Estimation",
    description="Estimate <X0X1> + <Z0Z1>",
    device_id="Kawasaki",
    shots=1000,
    program=program,
    operator=[
        OqtopusEstimationOperator(pauli="X 0 X 1", coeff=1.0),
        OqtopusEstimationOperator(pauli="Z 0 Z 1", coeff=1.0),
    ],
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_estimation(req, timeout=300.0)

print(result)
print(result.job_id, result.job_type)
print({"exp_value": result.exp_value, "stds": result.stds})
