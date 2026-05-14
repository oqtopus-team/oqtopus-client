"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
)

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

program1 = """OPENQASM 3;
include \"stdgates.inc\";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

program2 = """OPENQASM 3;
include \"stdgates.inc\";
qubit[1] q;
bit[1] c;

x q[0];
c[0] = measure q[0];
"""

req = OqtopusJobSpec.multi_manual(
    name="Multi Manual Example",
    description="Submit multi_manual job example",
    device_id="qulacs",
    shots=1000,
    program=[program1, program2],
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_multi_manual(req, timeout=300.0)

print(result)
print(result.job_id, result.job_type)
print(result.counts_with_integer_keys())
