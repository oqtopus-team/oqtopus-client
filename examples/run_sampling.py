from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
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

req = OqtopusJobSpec.sampling(
    name="Bell State Sampling",
    description="Bell state sampling example",
    device_id="Kawasaki",
    shots=1000,
    program=program,
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_sampling(req, timeout=300.0)

print(result)
print(result.job_id, result.job_type)
print(result.normalized_counts())
