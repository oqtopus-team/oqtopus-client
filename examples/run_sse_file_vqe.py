"""Submit SSE VQE runtime payload via oqtopus-client."""

from __future__ import annotations

import os
from pathlib import Path

from oqtopus_client import OqtopusClient, OqtopusConfig
from oqtopus_client.services.errors import ResponseValidationError
from oqtopus_client.services.job_results import OqtopusEstimationJobResult

section = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
config_path = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")
sse_script_path = Path(__file__).with_name("userprogram_vqe.py")

client = OqtopusClient(OqtopusConfig.from_file(section, path=config_path))
result = client.run_sse_file(
    file_path=sse_script_path,
    device_id="qulacs",
    name="SSE VQE Example",
    description="Submit SSE VQE job example",
    timeout=300.0,
)
print(result)
print(result.job_id, result.job_type)

typed_result = result.get_job_result()
if isinstance(typed_result, OqtopusEstimationJobResult):
    print({"exp_value": typed_result.exp_value, "stds": typed_result.stds})
else:
    print(f"Unexpected payload type: {type(typed_result).__name__}")
    print({"status": typed_result.status, "message": typed_result.message})

try:
    archive = result.download_log()
    print(f"SSE log archive size (memory only): {len(archive)} bytes")
except ResponseValidationError as exc:
    print(f"SSE log is unavailable: {exc}")
