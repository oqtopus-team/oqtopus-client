"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import (
    OqtopusClient,
    OqtopusConfig,
    OqtopusJobSpec,
    OqtopusSamplingJobResult,
)

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
    name="Run Job Generic",
    description="Use run_job helper with a sampling spec",
    device_id="Kawasaki",
    shots=1000,
    program=PROGRAM,
)

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
result = client.run_job(
    job_spec,
    interval=1.0,
    interval_backoff=1.1,
    max_interval=5.0,
    timeout=300.0,
)

print(result)
print(result.job_id, result.job_type)
if result.is_sampling():
    assert isinstance(result, OqtopusSamplingJobResult)
    print(result.normalized_counts())
