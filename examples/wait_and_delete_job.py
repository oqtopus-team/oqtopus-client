"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

PROGRAM = """OPENQASM 3;
include "stdgates.inc";
qubit[1] q;
bit[1] c;
h q[0];
c[0] = measure q[0];
"""

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
job_id = client.submit_job(
    OqtopusJobSpec.sampling(
        device_id="Kawasaki",
        shots=100,
        program=PROGRAM,
        name="Wait/Delete example",
    )
).job_id
result = client.wait_for_job(job_id, interval=1.0, timeout=300.0)
deleted = client.delete_job(job_id)

print("wait_for_job:", result.job_id, result.job_type)
print("delete_job:", deleted)
