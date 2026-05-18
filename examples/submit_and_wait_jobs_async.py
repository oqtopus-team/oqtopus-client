"""Usage example for oqtopus-client."""

from __future__ import annotations

import asyncio
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


async def do_other_work(label: str) -> None:
    """Simulate unrelated async work while job I/O is in flight."""
    print(f"{label}: preparing local summary...")
    await asyncio.sleep(0.2)
    print(f"{label}: local summary ready")


async def main() -> None:
    """Submit and wait for multiple jobs concurrently from an async context."""
    jobs = [
        OqtopusJobSpec.sampling(
            device_id="qulacs",
            shots=500,
            program=PROGRAM_A,
            name="Async Batch A",
        ),
        OqtopusJobSpec.sampling(
            device_id="qulacs",
            shots=500,
            program=PROGRAM_B,
            name="Async Batch B",
        ),
    ]

    client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
    submit_task = asyncio.create_task(client.submit_jobs_async(jobs, max_workers=2))

    print("submitting jobs in background...")
    await do_other_work("submit phase")

    responses = await submit_task
    print("submitted:", [response.job_id for response in responses])

    wait_task = asyncio.create_task(
        client.wait_for_jobs_async(
            [response.job_id for response in responses],
            interval=1.0,
            interval_backoff=1.1,
            max_interval=5.0,
            timeout=300.0,
            max_workers=2,
        )
    )

    print("waiting for jobs in background...")
    await do_other_work("wait phase")

    results = await wait_task
    print("finished:", [(result.job_id, str(result.status)) for result in results])


if __name__ == "__main__":
    asyncio.run(main())
