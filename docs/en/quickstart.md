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

## Recommended Configuration Flow

The recommended setup is to define the `default` profile in
`$XDG_CONFIG_HOME/oqtopus/config.ini` when `XDG_CONFIG_HOME` is set, or
`~/.config/oqtopus/config.ini` otherwise, and construct `OqtopusClient()`
without arguments.

Create the config file in that location:

```ini
[default]
base_url = <url>
api_token = <token>
```

Then initialize the client:

```python
from oqtopus_client import OqtopusClient

client = OqtopusClient()
print(client.list_devices())
```

`OqtopusClient()` uses `OqtopusConfig.from_file()` internally, and
`OqtopusConfig.from_file()` uses the `default` section when no profile is specified.

## Other Configuration Patterns

### Use a named profile from `config.ini`

Add additional sections when you need multiple environments:

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
print(client.list_devices())
```

### Load configuration from environment variables

```bash
export OQTOPUS_BASE_URL=<url>
export OQTOPUS_API_TOKEN=<token>
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
print(client.list_devices())
```

### Override configuration explicitly in code

Use explicit `OqtopusConfig(...)` when you need a one-off override:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(
    OqtopusConfig(
        base_url="<url>",
        api_token="<token>",
        retry_max_attempts=3,
        retry_backoff_seconds=0.2,
    )
)
print(client.list_devices())
```

The token is sent using the `q-api-token` request header.

Optional variables and settings include:

- `default_headers`: add common headers
- `user_agent`: override User-Agent

## First Job

For common workflows, you can use `OqtopusJobSpec` and `run_*` helpers so you do not need
to build generated OpenAPI request models manually.

The examples below use this shared OpenQASM program:

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

## Job Execution Styles

You can write job execution in two styles:

- `run_*` style: submit-and-wait with less code and without writing polling control yourself.
- `submit_job + wait` style: explicit `job_id` lifecycle control.

### Style 1: `run_*` (submit-and-wait)

Use `OqtopusClient.run_job()` to execute `submit + wait` in one call.
The client still polls job status internally until completion, but you do not need to
implement that lifecycle control yourself:

```python
from oqtopus_client import OqtopusClient, OqtopusJobSpec

req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=1000,
    program=program,
)

client = OqtopusClient()
finished_job = client.run_job(req, timeout=300.0)
print(finished_job.status)
```

You can also use job-type-specific shortcuts (raise `ValueError` on mismatch):

```python
sampling_req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=1000,
    program=program,
)
final_sampling = client.run_sampling(sampling_req)
print(final_sampling.submitted_at)
```

### Style 2: `submit_job + wait` (step-by-step)

To handle a submitted job in steps, use `job_id` with client methods:

```python
from oqtopus_client import OqtopusClient, OqtopusJobSpec

client = OqtopusClient()
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=1000,
    program=program,
)

job_id = client.submit_job(req).job_id
print(job_id)
print(client.status(job_id))
finished_job = client.wait(job_id, interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
print(finished_job.status)
```

## Further Reading

- [Examples](examples.md)
- [API Reference](api.md)
