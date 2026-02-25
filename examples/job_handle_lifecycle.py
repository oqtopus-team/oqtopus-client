from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobHandle, OqtopusJobSpec


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")

PROGRAM = """OPENQASM 3;
include "stdgates.inc";
qubit[1] q;
bit[1] c;
h q[0];
c[0] = measure q[0];
"""

job_spec = OqtopusJobSpec.sampling(
    name="Job Handle Lifecycle",
    description="Use OqtopusJobHandle methods end-to-end",
    device_id="Kawasaki",
    shots=500,
    program=PROGRAM,
)

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
submitted = client.submit_job(job_spec)
handle = OqtopusJobHandle(client, submitted.job_id)

print("initial_status:", handle.status())
print("is_finished:", handle.is_finished())

waited = handle.wait(interval=1.0, interval_backoff=1.1, max_interval=5.0, timeout=300.0)
refreshed = handle.refresh()
current = handle.get_current_result()
fetched = handle.get_result(timeout=1.0)
direct = client.get_job_result(handle.job_id)
status = client.get_job_status(handle.job_id)

print("waited:", waited.job_id, waited.job_type)
print("refreshed:", refreshed.job_id)
print("status:", status.status)
print("current:", current.job_id, current.job_type)
print("fetched:", fetched.job_id, fetched.job_type)
print("direct:", direct.job_id, direct.job_type)
