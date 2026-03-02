"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
devices = client.list_devices()
print("devices:", len(devices))
if devices:
    one = client.get_device(devices[0].device_id)
    print("first_device:", one.device_id, one.status, one.device_type)
    print("device_info:", one.device_info)
    print("basis_gates:", one.basis_gates)
    print("supported_instructions:", one.supported_instructions)

jobs = client.list_jobs(size=5)
print("jobs:", [job.job_id for job in jobs])
