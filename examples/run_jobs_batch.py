"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

PROGRAM_A = """OPENQASM 3;
include "stdgates.inc";
qubit[1] q;
bit[1] c;
h q[0];
c[0] = measure q[0];
"""

PROGRAM_B = """OPENQASM 3;
include "stdgates.inc";
qubit[1] q;
bit[1] c;
x q[0];
c[0] = measure q[0];
"""

jobs = [
    OqtopusJobSpec.sampling(device_id="Kawasaki", shots=500, program=PROGRAM_A, name="Batch A"),
    OqtopusJobSpec.sampling(device_id="Kawasaki", shots=500, program=PROGRAM_B, name="Batch B"),
]

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
batch_results = client.run_jobs_batch(
    jobs,
    submit_workers=2,
    wait_workers=2,
    interval=1.0,
    interval_backoff=1.1,
    max_interval=5.0,
    timeout=300.0,
)

print("batch_results:", [(r.job_id, str(r.job_type)) for r in batch_results])
