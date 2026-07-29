# Getting Started

## Installation

```bash
pip install oqtopus-client
```

The core client works without depending on other quantum software SDKs.

## Configuration

The recommended setup is to define the `default` profile and construct
`OqtopusClient()` without arguments.

`OqtopusConfig.from_file(section="default", path=...)` resolves the config file
as follows:

1. If you omit `path`, it reads `$XDG_CONFIG_HOME/oqtopus/config.ini` when
   `XDG_CONFIG_HOME` is set.
2. If you omit `path` and `XDG_CONFIG_HOME` is not set, it reads
   `~/.config/oqtopus/config.ini`.
3. If you specify `path`, it reads that location instead.

The `section` argument defaults to `default`, so `OqtopusClient()` and
`OqtopusConfig.from_file()` without arguments both load the `[default]` profile.

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
If you need a different setup, see [Other Configuration Patterns](#other-configuration-patterns).

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

Helpful API references for this section:

- [SDK Reference](../reference/index.md): entry point for the hand-written SDK
  reference and the generated OpenAPI reference.
- [Package Reference](../reference/sdk/oqtopus_client/index.md): API reference
  for `OqtopusJobSpec`, `OqtopusJobResult`, `OqtopusSamplingJobResult`, and
  `OqtopusEstimationJobResult`.

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
    device_id="qulacs",
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
    device_id="qulacs",
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
    device_id="qulacs",
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

### Style 3: async batch submit/wait

In an async context, you can submit and wait for multiple jobs with
`submit_jobs_async()` and `wait_for_jobs_async()`:

Synchronous `OqtopusClient` methods use `asyncio.run()` internally when no
event loop is running. In environments such as Jupyter notebooks where an
event loop is already running, they execute the internal async work in a worker
thread. For fully non-blocking async code, use async APIs such as
`submit_jobs_async()` and `wait_for_jobs_async()`.

```python
import asyncio

from oqtopus_client import OqtopusClient, OqtopusJobSpec

async def main() -> None:
    client = OqtopusClient()
    jobs = [
        OqtopusJobSpec.sampling(
            device_id="qulacs",
            shots=1000,
            program=program,
            name="async-job-1",
        ),
        OqtopusJobSpec.sampling(
            device_id="qulacs",
            shots=1000,
            program=program,
            name="async-job-2",
        ),
    ]

    submit_task = asyncio.create_task(client.submit_jobs_async(jobs, max_workers=2))

    print("submitting in background...")
    await asyncio.sleep(0.2)
    print("prepared a local summary while submit was running")

    responses = await submit_task

    wait_task = asyncio.create_task(
        client.wait_for_jobs_async(
            [response.job_id for response in responses],
            interval=1.0,
            interval_backoff=1.2,
            max_interval=5.0,
            timeout=300.0,
            max_workers=2,
        )
    )

    print("waiting in background...")
    await asyncio.sleep(0.2)
    print("updated a progress message while waiting")

    finished_jobs = await wait_task
    print([job.status for job in finished_jobs])

asyncio.run(main())
```

Example output:

```text
submitting in background...
prepared a local summary while submit was running
waiting in background...
updated a progress message while waiting
[<JobsJobStatus.SUCCEEDED: 'succeeded'>, <JobsJobStatus.SUCCEEDED: 'succeeded'>]
```

## Check Job Results

After a sampling job succeeds, you can inspect the measured counts from the returned
result object:

```python
from oqtopus_client import OqtopusClient, OqtopusJobSpec

client = OqtopusClient()
req = OqtopusJobSpec.sampling(
    device_id="qulacs",
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

You can also point to a different file explicitly:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(
    OqtopusConfig.from_file(
        section="oqtopus-dev",
        path="~/custom-config/oqtopus/config.ini",
    )
)
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

`from_env()` reads `OQTOPUS_BASE_URL` for the base URL, `OQTOPUS_API_TOKEN` for
the API token, and `OQTOPUS_PROXY` for the optional proxy by default.

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

By default, automatic retries apply only to HTTP `429` responses. If you need a
different policy, set `retry_status_codes` explicitly.

The API token is sent using both the `q-api-token` and `Authorization` request headers with the same value.

Optional variables and settings include:

- `default_headers`: add common headers
- `user_agent`: override User-Agent

For more detail on config, client APIs, and generated bindings, see the
[API Reference](../reference/index.md).

## Further Reading

- [Examples](examples.md)
- [`examples/` directory on GitHub](https://github.com/oqtopus-team/oqtopus-client/tree/main/examples)
- [API Reference](../reference/index.md)
