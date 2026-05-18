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

job_spec = OqtopusJobSpec.sampling(
    name="Job Lifecycle",
    description="Use client job methods end-to-end",
    device_id="qulacs",
    shots=500,
    program=PROGRAM,
)

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
job_id = client.submit_job(job_spec).job_id

print("initial_status:", client.status(job_id))
print("is_finished:", client.is_finished(job_id))

waited = client.wait(
    job_id,
    interval=1.0,
    interval_backoff=1.1,
    max_interval=5.0,
    timeout=300.0,
)
refreshed = client.refresh(job_id)
current = client.result(job_id)
fetched = client.wait(job_id, timeout=1.0)
direct = client.get_job(job_id)
status = client.get_job_status(job_id)

print("waited:", waited.job_id, waited.job_type)
print("refreshed:", refreshed.job_id)
print("status:", status.status)
print("current:", current.job_id, current.job_type)
print("fetched:", fetched.job_id, fetched.job_type)
print("direct:", direct.job_id, direct.job_type)
