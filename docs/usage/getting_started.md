# Getting Started

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

The recommended setup is to define the `default` profile and construct
`OqtopusClient()` without arguments.

`OqtopusConfig.from_file()` resolves the config file path as follows:

1. If you do not specify `path`, it reads the default config location.
2. If you specify `path`, it reads that location.
3. When `path` is not specified and `XDG_CONFIG_HOME` is set, the default
   location is `$XDG_CONFIG_HOME/oqtopus/config.ini`; otherwise it is
   `~/.config/oqtopus/config.ini`.

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
```

### Load configuration from environment variables

```bash
export OQTOPUS_BASE_URL=<url>
export OQTOPUS_API_TOKEN=<token>
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
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

Example output:

```text
succeeded
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

Example output:

```text
2026-03-11 18:30:12+00:00
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

Example output:

```text
069b1464-c124-79b3-8000-fb41f3dfdc50
submitted
succeeded
```

## Check Job Results

After a sampling job succeeds, you can inspect the measured counts from the returned
result object:

```python
from oqtopus_client import OqtopusClient, OqtopusJobSpec

client = OqtopusClient()
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=1000,
    program=program,
)

finished_job = client.run_sampling(req, timeout=300.0)
print(finished_job.get_counts())
```

Example output:

```text
{'00': 506, '11': 494}
```

## Job Status Values

`finished_job.status` and `client.status(job_id)` return one of these values:

- `submitted`: the job was accepted and queued.
- `ready`: the job is prepared and waiting to start.
- `running`: the job is executing.
- `succeeded`: the job finished successfully.
- `failed`: the job finished with an error.
- `cancelled`: the job was cancelled before successful completion.

When you use `run_*()` or `wait()`, the returned job is already finished, so its
status is typically `succeeded`, `failed`, or `cancelled`.

## Further Reading

- [Examples](examples.md)
- [`examples/` directory on GitHub](https://github.com/oqtopus-team/oqtopus-client/tree/main/examples)
- [API Reference](../reference/API_reference.md)
