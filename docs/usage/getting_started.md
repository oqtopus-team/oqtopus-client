# Getting Started

## Install

```bash
pip install oqtopus-client
```

The core client works without depending on other quantum software SDKs.

## Basic usage

You can write job execution in two styles:

- `run_*` style: one-shot `submit + wait` with less code.
- `submit_job + wait` style: explicit `job_id` lifecycle control.

Both styles are supported with `OqtopusJobSpec` helper methods, so you can avoid manually constructing generated OpenAPI models.

### Style 1: `run_*` (one-shot)

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
    shots=1000,
)
result = client.run_sampling(req, timeout=300.0)
print(result.job_id)
print(result.get_counts())
```

### Style 2: `submit_job + wait` (step-by-step)

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
    shots=1000,
)

job_id = client.submit_job(req).job_id
print("submitted:", job_id)
print("status:", client.status(job_id))

result = client.wait(job_id, interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
print(result.job_id)
print(result.get_counts())
```

## Authentication via environment variables

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
print(client.list_devices())
```

## Authentication via config file

Create `~/.config/oqtopus/config.ini`:

```ini
[oqtopus-dev]
base_url = https://api.example.com
api_token = <token>
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))
print(client.list_devices())
```

## Further Reading

- [API reference overview](../reference/index.md)
