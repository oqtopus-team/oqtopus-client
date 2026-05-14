"""Usage example for oqtopus-client."""

from __future__ import annotations

import os
from pathlib import Path

from oqtopus_client import OqtopusClient, OqtopusConfig

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")
sse_script_path = Path(__file__).with_name("userprogram.py")

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_sse_file(
    file_path=sse_script_path,
    device_id="qulacs",
    name="SSE Example",
    description="Submit sse job example",
    timeout=300.0,
)
print(result)
print(result.job_id, result.job_type)
print(result.counts_with_integer_keys())

archive = result.download_log()
print(f"SSE log archive size (memory only): {len(archive)} bytes")
print("SSE log content:")
result.show_log()
