from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
    OqtopusSamplingJobResult,
)

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
    name="Get Job Example",
    description="Create a job and retrieve it",
    device_id="Kawasaki",
    shots=100,
    program=program,
)

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
submitted_job = client.submit_job(req)
fetched_job = client.get_job(submitted_job.job_id)
current_result = client.result(submitted_job.job_id)
status = client.status(submitted_job.job_id)

print(fetched_job)
print(fetched_job.job_id)
if isinstance(current_result, OqtopusSamplingJobResult):
    print(current_result.normalized_counts())
print("status:", status)
