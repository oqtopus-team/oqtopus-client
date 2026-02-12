from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
    OqtopusSamplingJobResult,
)

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")

program_bell = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

program_single = """OPENQASM 3;
include "stdgates.inc";
qubit[1] q;
bit[1] c;

h q[0];
c[0] = measure q[0];
"""

jobs = [
    OqtopusJobSpec.sampling(
        name="Parallel Sampling 1",
        description="BatchRunner parallel example 1",
        device_id="Kawasaki",
        shots=1000,
        program=program_bell,
    ),
    OqtopusJobSpec.sampling(
        name="Parallel Sampling 2",
        description="BatchRunner parallel example 2",
        device_id="Kawasaki",
        shots=1000,
        program=program_single,
    ),
]

with OqtopusClient(OqtopusConfig.from_file(section, path=config_path)) as client:
    submitted_jobs = client.submit_jobs(jobs, max_workers=2)
    submitted_job_ids = [job.job_id for job in submitted_jobs]
    print("submitted:", submitted_job_ids)

    finished_jobs = client.wait_for_jobs(
        submitted_job_ids,
        interval=1.0,
        interval_backoff=1.1,
        max_interval=5.0,
        timeout=300.0,
        max_workers=2,
    )

for finished_job in finished_jobs:
    print(finished_job.job_id, finished_job.job_type)
    if isinstance(finished_job, OqtopusSamplingJobResult):
        print("counts:", finished_job.get_counts())
