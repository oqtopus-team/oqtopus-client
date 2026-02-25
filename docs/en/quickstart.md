# Quickstart

## Installation

```bash
pip install oqtopus-client
```

The core client works without depending on other quantum software SDKs.

For local development:

```bash
pip install -e .
```

## Authentication

`OqtopusClient` supports either:

- `api_token`: direct token string (recommended)

The token is sent using the `q-api-token` request header.

For common workflows, you can use `OqtopusJobSpec` and `run_*` helpers so you do not need to build generated OpenAPI request models manually.

## Minimal Example

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
devices = client.list_devices()
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=1000,
    program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
)
job_id = client.submit_job(req).job_id
print(job_id)
```

## Initialize From Environment Variables

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
print(client.list_devices())
```

Optional variables and settings:

- `default_headers`: add common headers
- `user_agent`: override User-Agent

## Job Execution Styles

You can write job execution in two styles:

- `run_*` style: one-shot `submit + wait` with less code.
- `submit_job + wait` style: explicit `job_id` lifecycle control.

### Style 1: `run_*` (one-shot)

Use `OqtopusClient.run_job()` to execute `submit + wait` in one call:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

req = models.JobsSubmitJobRequest(
    device_id="Kawasaki",
    job_type=models.JobsJobType.SAMPLING,
    shots=100,
    job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
)

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
finished_job = client.run_job(req, timeout=300.0)
print(finished_job.status)
```

You can also use job-type-specific shortcuts (raise `ValueError` on mismatch):

```python
final_sampling = client.run_sampling(sampling_req)
final_estimation = client.run_estimation(estimation_req)
final_manual = client.run_multi_manual(multi_manual_req)
final_sse = client.run_sse(sse_req)
```

### Style 2: `submit_job + wait` (step-by-step)

To handle a submitted job in steps, use `job_id` with client methods:

```python
job_id = client.submit_job(req).job_id
print(job_id)
print(client.status(job_id))
finished_job = client.wait(job_id, interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
```
