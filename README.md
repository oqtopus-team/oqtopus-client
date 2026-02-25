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

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
    shots=1000,
)
finished_job = client.run_sampling(req, interval=2.0, timeout=300.0)
print(finished_job.status)
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
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/main/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/models
```

To initialize from environment variables, use `OqtopusConfig.from_env()`.

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
print(client.list_devices())
```

You can tune retry behavior via initialization arguments (default: retry `GET/DELETE` on 429/5xx).

```python
from oqtopus_client import OqtopusClient
from oqtopus_client import OqtopusConfig

client = OqtopusClient(
    OqtopusConfig(
        base_url="https://api.example.com",
        api_token="<token>",
        retry_max_attempts=3,
        retry_backoff_seconds=0.2,
    ),
)
print(client.list_devices())
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
- `job_handle_lifecycle.py (status / wait / result / cancel helpers)`
- `run_jobs_batch.py (OqtopusClient.run_jobs_batch)`
- `wait_and_delete_job.py (wait_for_job / delete_job)`
- `manage_api_token.py (create_api_token / delete_api_token)`
- `get_announcement_detail.py (get_announcements_list / get_announcement)`
- `init_client_from_env.py (OqtopusConfig.from_env / set_api_token / client attributes)`
- `list_devices_and_jobs.py (list_devices / get_device / list_jobs)`
- `get_user_and_status.py (get_announcements_list / get_api_token)`
- `get_job.py`
- `cancel_job.py`

Basic style:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))
print(client.list_devices())
```

Run example:

```bash
python examples/get_devices.py
```

A helper class is available to parallelize submit/wait across multiple jobs.

```python
responses = client.submit_jobs([req1, req2], max_workers=2)
finished_jobs = client.wait_for_jobs([r.job_id for r in responses], max_workers=2)
```

For step-by-step job control, use `job_id` with client methods.

```python
job_id = client.submit_job(req).job_id
print(client.status(job_id))
finished_job = client.wait(job_id, interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
print(finished_job.status)
```

One-shot submit+wait and batch helper APIs are also provided.

```python
finished_job = client.run_job(req, timeout=300.0)
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

- OpenAPI schema is fetched with `make download-oas` into `spec/openapi.yaml` (gitignored)
- `spec/Makefile`: runs `download-oas` (latest OAS fetch) and `openapi-generator`
- `Makefile`: wrapper for `spec/Makefile`
- `docs/`: API and usage documentation
- `mkdocs.yml`: documentation build settings
- `src/oqtopus_client/models/generated/`: generated models (openapi-generator output)
- `src/oqtopus_client/client.py`: SDK client using generated models
- `examples/`: SDK usage examples
- `tests/`: SDK tests
