"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from quri_parts.circuit import QuantumCircuit
from quri_parts.openqasm.circuit import convert_to_qasm_str

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
)

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")


circuit = QuantumCircuit(2, cbit_count=2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)
qasm = convert_to_qasm_str(circuit)

req = OqtopusJobSpec.sampling(
    name="Bell State Sampling (QURI Parts)",
    description="Submit sampling job from QURI Parts circuit",
    device_id="Kawasaki",
    shots=1000,
    program=qasm,
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_sampling(req, timeout=300.0)

print(result)
print(result.job_id, result.job_type)
print(result.counts_with_integer_keys())
