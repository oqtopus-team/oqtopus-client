# Models

Pydantic models generated from OpenAPI.
This page lists commonly used models first, then provides the full generated model reference.

## Frequently Used Models

### 1) Job submission

::: oqtopus_client.generated.JobsSubmitJobRequest

::: oqtopus_client.generated.JobsSubmitJobInfo

### 2) Job status polling

::: oqtopus_client.generated.JobsGetJobStatusResponse

::: oqtopus_client.generated.JobsJobStatus

### 3) Job details and results

::: oqtopus_client.generated.JobsJobDef

::: oqtopus_client.generated.JobsJobInfo

::: oqtopus_client.generated.JobsJobResult

::: oqtopus_client.generated.JobsSamplingResult

### 4) Device information

::: oqtopus_client.generated.DevicesDeviceInfo

## Minimal Model Usage

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    shots=100,
    program="OPENQASM 3; qubit[1] q;",
)

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
job_id = client.submit_job(req).job_id
status = client.get_job_status(job_id)
finished_job = client.wait_for_job(job_id, timeout=300.0)
print(status.status, finished_job.job_info.result)
```

## Full Generated Model Reference

::: oqtopus_client.generated
