"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from qiskit import QuantumCircuit, qasm3  # type: ignore[import-untyped]

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
)

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

circuit = QuantumCircuit(2, 2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure([0, 1], [0, 1])
qasm = qasm3.dumps(circuit)

req = OqtopusJobSpec.sampling(
    name="Bell State Sampling (Qiskit)",
    description="Submit sampling job from Qiskit circuit",
    device_id="Kawasaki",
    shots=1000,
    program=qasm,
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_sampling(req, timeout=300.0)

print(result)
print(result.job_id, result.job_type)
print(result.counts_with_integer_keys())
