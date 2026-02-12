# Models

Pydantic models generated from OpenAPI.
This page lists commonly used models first, then provides the full generated model reference.

## Frequently Used Models

### 1) Job submission

::: oqtopus_client.models.generated.JobsSubmitJobRequest

::: oqtopus_client.models.generated.JobsSubmitJobInfo

### 2) Job status polling

::: oqtopus_client.models.generated.JobsGetJobStatusResponse

::: oqtopus_client.models.generated.JobsJobStatus

### 3) Job details and results

::: oqtopus_client.models.generated.JobsJobDef

::: oqtopus_client.models.generated.JobsJobInfo

::: oqtopus_client.models.generated.JobsJobResult

::: oqtopus_client.models.generated.JobsSamplingResult

### 4) Device information

::: oqtopus_client.models.generated.DevicesDeviceInfo

### 5) User profile

::: oqtopus_client.models.generated.UsersGetOneUserResponse

::: oqtopus_client.models.generated.UsersUpdateUserRequest

## Minimal Model Usage

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

req = models.JobsSubmitJobRequest(
    device_id="Kawasaki",
    job_type=models.JobsJobType.SAMPLING,
    shots=100,
    job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
)

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    submitted = client.submit_job(req)
    status = client.get_job_status(submitted.job_id)
    finished_job = client.wait_for_job(submitted.job_id, timeout=300.0)
    print(status.status, finished_job.job_info.result)
```

## Full Generated Model Reference

::: oqtopus_client.models.generated
