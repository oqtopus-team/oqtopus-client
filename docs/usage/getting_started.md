# Getting Started

This page explains the minimum flow to run your first job with `oqtopus-client`.
It focuses on practical usage first, then shows configuration patterns for local development and team operation.

## Install

```bash
pip install oqtopus-client
```

The core client works without depending on other quantum software SDKs.

## Before you run code

Prepare the following values:

- `base_url`: OQTOPUS Cloud User API endpoint (`<url>`)
- `api_token`: your API token (`<token>`)
- `device_id`: target backend device id (for example, `Kawasaki`)

The examples below use `OqtopusJobSpec`, which keeps request construction simple and type-safe.

## Basic usage

`OqtopusClient` supports two execution styles:

- `run_*` style: one-shot `submit + wait`
- `submit_job + wait` style: explicit lifecycle control with `job_id`

### Common OpenQASM program

For gates such as `h` and `cx`, include `stdgates.inc`:

```python
program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c = measure q;
"""
```

### Style 1: `run_*` (one-shot)

Use this style when you want concise code and do not need intermediate polling logic.

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c = measure q;
"""

client = OqtopusClient(OqtopusConfig(base_url="<url>", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program=program,
    shots=1000,
)
result = client.run_sampling(req, timeout=300.0)
print(result.job_id)
print(result.status)
print(result.get_counts())
```

Sample output:

```text
job-1234567890
JobsJobStatus.SUCCEEDED
{'00': 503, '11': 497}
```

### Style 2: `submit_job + wait` (step-by-step)

Use this style when you need explicit control (for example, custom polling or external job tracking).

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c = measure q;
"""

client = OqtopusClient(OqtopusConfig(base_url="<url>", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program=program,
    shots=1000,
)

job_id = client.submit_job(req).job_id
print("submitted:", job_id)
print("status:", client.status(job_id))

result = client.wait(
    job_id,
    interval=1.0,
    interval_backoff=1.2,
    max_interval=5.0,
    timeout=300.0,
)
print("final:", result.status)
print("counts:", result.get_counts())
```

Sample output:

```text
submitted: job-1234567890
status: JobsJobStatus.RUNNING
final: JobsJobStatus.SUCCEEDED
counts: {'00': 503, '11': 497}
```

## Authentication via environment variables

This is useful in CI or container environments where secrets are injected via env vars.

```bash
export OQTOPUS_BASE_URL="<url>"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
devices = client.list_devices()
print(len(devices))
print(devices[0].device_id if devices else "no devices")
```

Sample output:

```text
3
Kawasaki
```

## Authentication via config file

`OqtopusConfig.from_file()` reads `~/.config/oqtopus/config.ini`.
If no section is specified, it uses `default`.

### 1. Define `default` profile (used by default)

Create `~/.config/oqtopus/config.ini`:

```ini
[default]
base_url = <url>
api_token = <token>
```

```python
from oqtopus_client import OqtopusClient

client = OqtopusClient()  # internally uses OqtopusConfig.from_file("default")
print(client.base_url)
```

Sample output:

```text
<url>
```

### 2. Add named profile and select it explicitly

For multiple environments (dev/staging/prod), add additional sections:

```ini
[default]
base_url = <url>
api_token = <token>

[oqtopus-dev]
base_url = <url>
api_token = <token>
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_file("oqtopus-dev"))
devices = client.list_devices()
print(len(devices))
```

Sample output:

```text
3
```

## Further reading

- [API reference overview](../reference/index.md)
