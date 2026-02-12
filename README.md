# oqtopus-client

Python SDK for the OQTOPUS Cloud User API.

## Key Characteristics

- Core client usage has no runtime dependency on other quantum software SDKs.
- Optional integration examples may require extra packages (for example, `qiskit` or `quri-parts`).
- OpenAPI-generated models are used internally, while helper APIs such as `OqtopusJobSpec` and `run_*` keep common usage simple.
- HTTP communication is executed asynchronously inside the client runtime, while a synchronous API is exposed for ease of use.
- Built-in retry/backoff controls and typed result wrappers improve operational robustness.

## Quick Example

```python
from oqtopus_client import OqtopusJobSpec, OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    req = OqtopusJobSpec.sampling(
        device_id="Kawasaki",
        program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
        shots=1000,
    )
    final_job = client.run_sampling(req, interval=2.0, timeout=300.0)
    print(final_job.status)
```

## Installation

```bash
pip install oqtopus-client
```

For local development:

```bash
pip install -e ".[dev]"
```

## Usage

Generate/download OAS-derived models:

```bash
make download-oas
make generate-models
```

If needed, you can override the source URL and output destination.

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/models/generated/models
```

To initialize from environment variables, use `OqtopusConfig.from_env()`.

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_env()) as client:
    print(client.list_devices())
```

You can tune retry behavior via initialization arguments (default: retry `GET/DELETE` on 429/5xx).

```python
from oqtopus_client import OqtopusClient
from oqtopus_client import OqtopusConfig

with OqtopusClient(
    OqtopusConfig(
        base_url="https://api.example.com",
        api_token="<token>",
        retry_max_attempts=3,
        retry_backoff_seconds=0.2,
    ),
) as client:
    print(client.list_devices())
```

You can also add default headers and override `User-Agent`.

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(
    OqtopusConfig(base_url="https://api.example.com", api_token="<token>"),
    default_headers={"X-Trace-ID": "trace-123"},
    user_agent="my-app/1.0.0",
) as client:
    print(client.get_current_user())
```

## examples

`examples/` contains runnable Python examples.

- `get_devices.py`
- `run_sampling.py (run_sampling)`
- `run_estimation.py (run_estimation)`
- `run_multi_manual.py (run_multi_manual)`
- `run_sse_file.py (run_sse_file, SSE logs are handled in memory by default. Persist explicitly with `download_log(..., persist=True)`)`
- `run_sampling_qiskit.py`
- `run_sampling_quri_parts.py`
- `submit_jobs_parallel.py (OqtopusClient.submit_jobs / wait_for_jobs)`
- `run_job_generic.py (OqtopusClient.run_job)`
- `job_handle_lifecycle.py (OqtopusJobHandle methods)`
- `run_jobs_batch.py (OqtopusClient.run_jobs_batch)`
- `wait_and_delete_job.py (wait_for_job / delete_job)`
- `manage_api_token.py (create_api_token / delete_api_token)`
- `get_announcement_detail.py (get_announcements_list / get_announcement)`
- `init_client_from_env.py (OqtopusConfig.from_env / set_api_token / client attributes)`
- `list_devices_and_jobs.py (list_devices / get_device / list_jobs)`
- `get_user_and_status.py (get_current_user / get_announcements_list / get_api_token_status)`
- `get_job.py`
- `cancel_job.py`

Basic style:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_file("oqtopus-dev")) as client:
    print(client.list_devices())
```

Run example:

```bash
python examples/get_devices.py
```

The Qiskit-based submission example requires this extra dependency.

```bash
pip install qiskit
```

You can also use a utility that converts sampling-result bitstring keys to integer keys.

```python
from oqtopus_client import normalize_sampling_result

normalized = normalize_sampling_result(final_job.job_info.result.sampling)
print(normalized["counts"])
```

A utility for lock-safe API token file updates is also available.

```python
from oqtopus_client import write_api_token_file

write_api_token_file("credentials/token.json", "new-token", as_json=True)
```

A helper class is available to parallelize submit/wait across multiple jobs.

```python
responses = client.submit_jobs([req1, req2], max_workers=2)
final_jobs = client.wait_for_jobs([r.job_id for r in responses], max_workers=2)
```

Use `OqtopusJobHandle` when you want to manage an already-submitted job step by step.

```python
from oqtopus_client import OqtopusJobHandle

submitted_job = client.submit_job(req)
job = OqtopusJobHandle(client, submitted_job.job_id)
print(job.status())
final_job = job.wait(interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
print(final_job.status)
```

One-shot submit+wait and batch helper APIs are also provided.

```python
final_job = client.run_job(req, timeout=300.0)
batch_results = client.run_jobs_batch([req1, req2], submit_workers=2, wait_workers=2)
```

## tests

```bash
make test
```

## quality

```bash
pip install -e ".[dev]"
make lint
make typecheck
make check
```

## docs

API documentation can be generated automatically from docstrings.

```bash
pip install -e ".[dev]"
```

```bash
make docs
```

Local preview:

```bash
make docs-serve
```

## Project layout

- `spec/openapi.yaml`: source OAS used for model generation
- `spec/Makefile`: runs `download-oas` (latest OAS fetch) and `openapi-generator`
- `Makefile`: wrapper for `spec/Makefile`
- `docs/`: API and usage documentation
- `mkdocs.yml`: documentation build settings
- `src/oqtopus_client/models/generated/`: generated models (openapi-generator output)
- `src/oqtopus_client/client.py`: SDK client using generated models
- `examples/`: SDK usage examples
- `tests/`: SDK tests
