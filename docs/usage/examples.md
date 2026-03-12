# Examples

Python script samples are available under `examples/`.

## Recommended Baseline

Most examples assume the recommended default-profile setup:

```ini
[default]
base_url = <url>
api_token = <token>
```

```python
from oqtopus_client import OqtopusClient

client = OqtopusClient()
```

Run an example script with:

```bash
python examples/get_devices.py
```

## Example Index

### Device and account inspection

- `get_devices.py`: list available devices.
- `list_devices_and_jobs.py`: inspect devices and recent jobs together.
- `get_user_and_status.py`: inspect account-level information.
- `manage_api_token.py`: create and delete API tokens.
- `get_announcement_detail.py`: list announcements and fetch a detail entry.

### Single-job execution

- `run_sampling.py`: execute a sampling job with `run_sampling`.
- `run_estimation.py`: execute an estimation job.
- `run_multi_manual.py`: execute a multi-manual job.
- `run_job_generic.py`: use `OqtopusClient.run_job`.
- `job_handle_lifecycle.py`: control a job with `status`, `wait`, `result`, and `cancel_job`.
- `wait_and_delete_job.py`: wait for completion and then delete a job.
- `get_job.py`: fetch one job by id.
- `cancel_job.py`: cancel a submitted job.

### Parallel and batch helpers

- `submit_jobs_parallel.py`: submit multiple jobs with `submit_jobs` and wait with `wait_for_jobs`.
- `run_jobs_batch.py`: combine batch submission and waiting with `run_jobs_batch`.

Parallel submit/wait is useful when you want explicit control over submission and waiting workers:

```python
responses = client.submit_jobs([req1, req2], max_workers=2)
finished_jobs = client.wait_for_jobs([response.job_id for response in responses], max_workers=2)
```

`run_jobs_batch` is a shorter helper when the full flow is "submit all, then wait for all":

```python
results = client.run_jobs_batch([req1, req2], submit_workers=2, wait_workers=2)
```

### Integration-specific examples

- `run_sampling_quri_parts.py`: run a sampling flow with QURI Parts integration.
- `run_sampling_qiskit.py`: run a sampling flow with Qiskit integration.
- `run_sse_file.py`: submit `examples/userprogram.py` as an SSE job and inspect logs.
- `init_client_from_env.py`: initialize from `OqtopusConfig.from_env()`.

## Extra Notes

`run_sse_file.py` handles SSE logs in memory by default. Persist them explicitly with
`download_log(..., persist=True)` when needed.

The `Qiskit` example requires an extra dependency:

```bash
pip install qiskit
```

The `QURI Parts` example requires extra dependencies as well:

```bash
pip install quri-parts-circuit quri-parts-openqasm
```

Result normalization helper:

```python
from oqtopus_client import normalize_sampling_result

normalized = normalize_sampling_result(finished_job.job_info.result.sampling)
print(normalized["counts"])
```
