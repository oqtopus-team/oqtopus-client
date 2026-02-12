from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")

with OqtopusClient(OqtopusConfig.from_file(section, path=config_path)) as client:
    devices = client.list_devices()

print(devices)
for device in devices:
    print(f"{device.device_id}: {device.status}")
