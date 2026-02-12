from __future__ import annotations

import os
from pathlib import Path

from oqtopus_client import OqtopusClient, OqtopusConfig

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")
sse_script_path = Path(__file__).with_name("userprogram.py")

with OqtopusClient(OqtopusConfig.from_file(section, path=config_path)) as client:
    result = client.run_sse_file(
        file_path=sse_script_path,
        device_id="Kawasaki",
        name="SSE Example",
        description="Submit sse job example",
        timeout=300.0,
    )
    print(result)
    print(result.job_id, result.job_type)
    print(result.normalized_counts())

    archive = result.download_log()
    print(f"SSE log archive size (memory only): {len(archive)} bytes")
    print("SSE log content:")
    result.show_log()
