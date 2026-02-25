# Examples

Python script samples are available under `examples/`:

- `get_devices.py`
- `run_sampling.py`
- `run_estimation.py`
- `run_multi_manual.py`
- `run_sse_file.py`
- `run_sampling_quri_parts.py`
- `run_sampling_qiskit.py`
- `submit_jobs_parallel.py` (`OqtopusClient.submit_jobs` / `wait_for_jobs`)
- `run_job_generic.py` (`OqtopusClient.run_job`)
- `job_handle_lifecycle.py` (`OqtopusJobHandle` methods)
- `run_jobs_batch.py` (`run_jobs_batch`)
- `wait_and_delete_job.py` (`wait_for_job`, `delete_job`)
- `manage_api_token.py` (`create_api_token`, `delete_api_token`)
- `get_announcement_detail.py` (`get_announcements_list`, `get_announcement`)
- `init_client_from_env.py` (`from_env`, `set_api_token`, client config attributes)
- `list_devices_and_jobs.py` (`list_devices`, `get_device`, `list_jobs`)
- `get_user_and_status.py` (`get_announcements_list`, `get_api_token`)
- `get_job.py`
- `cancel_job.py`

Simple style:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))
finished_job = client.run_job(request, timeout=300.0)
print(finished_job.status)
```

Run:

```bash
python examples/get_devices.py
```

Additional dependency for the Qiskit example:

```bash
pip install qiskit
```

`run_sse_file.py` submits `examples/userprogram.py` as an SSE job, then
downloads and prints SSE logs.

Wait for job completion:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
submitted_job = client.submit_job(request)
finished_job = client.wait_for_job(submitted_job.job_id, interval=2.0, timeout=300.0)
print(finished_job.status)
```

Result normalization helper:

```python
from oqtopus_client import normalize_sampling_result

normalized = normalize_sampling_result(finished_job.job_info.result.sampling)
print(normalized["counts"])
```

## Language

- English only
