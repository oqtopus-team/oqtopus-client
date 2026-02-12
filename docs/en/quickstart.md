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

- `api_token`: direct token string
- `api_token_file`: load token from file

Supported token file formats:

```text
<plain token>
```

```json
{"api_token_secret":"<token>"}
```

For common workflows, you can use `OqtopusJobSpec` and `run_*` helpers so you do not need to build generated OpenAPI request models manually.

## Minimal Example

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    devices = client.list_devices()
    req = models.JobsSubmitJobRequest(
        device_id="Kawasaki",
        job_type=models.JobsJobType.SAMPLING,
        shots=1000,
        job_info=models.JobsSubmitJobInfo(
            program=["OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;"]
        ),
    )
    job = client.submit_job(req)
    print(job.job_id)
```

## Initialize From Environment Variables

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_env()) as client:
    print(client.list_devices())
```

Optional variables and settings:

- `OQTOPUS_API_TOKEN_FILE`: token file path
- `default_headers`: add common headers
- `user_agent`: override User-Agent

## High-level Job Helpers

Use `OqtopusClient.run_job()` to execute `submit + wait` in one call:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

req = models.JobsSubmitJobRequest(
    device_id="Kawasaki",
    job_type=models.JobsJobType.SAMPLING,
    shots=100,
    job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
)

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    final_job = client.run_job(req, timeout=300.0)
    print(final_job.status)
```

You can also use job-type-specific shortcuts (raise `ValueError` on mismatch):

```python
final_sampling = client.run_sampling(sampling_req)
final_estimation = client.run_estimation(estimation_req)
final_manual = client.run_multi_manual(multi_manual_req)
final_sse = client.run_sse(sse_req)
```

To handle a submitted job in steps, use `OqtopusJobHandle`:

```python
from oqtopus_client import OqtopusJobHandle

submitted_job = client.submit_job(req)
job = OqtopusJobHandle(client, submitted_job.job_id)
print(job.job_id)
print(job.status())
final_job = job.wait(interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
```

## Language

- [日本語版](../ja/quickstart.md)
