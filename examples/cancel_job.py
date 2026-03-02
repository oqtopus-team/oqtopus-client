"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

program = """OPENQASM 3;
include \"stdgates.inc\";
qubit[1] q;
bit[1] c;

h q[0];
c[0] = measure q[0];
"""

req = OqtopusJobSpec.sampling(
    name="Cancel Job Example",
    description="Create a job and cancel it",
    device_id="Kawasaki",
    shots=100,
    program=program,
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
job_id = client.submit_job(req).job_id
result = client.cancel_job(job_id)

print(result)
