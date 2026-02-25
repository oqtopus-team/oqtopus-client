# Models

OpenAPI から自動生成された Pydantic モデルです。  
このページは「最初に読むべき主要モデル」を先に示し、最後に全モデル参照を置いています。

## まず使う主要モデル

### 1) ジョブ投入

`submit_job()` に渡す入力モデルです。

::: oqtopus_client.models.generated.JobsSubmitJobRequest

::: oqtopus_client.models.generated.JobsSubmitJobInfo

### 2) ジョブ状態確認

`get_job_status()` や `wait_for_job()` で扱う状態モデルです。

::: oqtopus_client.models.generated.JobsGetJobStatusResponse

::: oqtopus_client.models.generated.JobsJobStatus

### 3) ジョブ詳細・結果

完了後に `get_job()` / `wait_for_job()` で得るモデルです。

::: oqtopus_client.models.generated.JobsJobDef

::: oqtopus_client.models.generated.JobsJobInfo

::: oqtopus_client.models.generated.JobsJobResult

::: oqtopus_client.models.generated.JobsSamplingResult

### 4) デバイス情報

利用可能デバイスの取得に使うモデルです。

::: oqtopus_client.models.generated.DevicesDeviceInfo

## 最小利用例

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

req = models.JobsSubmitJobRequest(
    device_id="Kawasaki",
    job_type=models.JobsJobType.SAMPLING,
    shots=100,
    job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
)

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
submitted = client.submit_job(req)
status = client.get_job_status(submitted.job_id)
finished_job = client.wait_for_job(submitted.job_id, timeout=300.0)
print(status.status, finished_job.job_info.result)
```

## 全モデル参照

必要に応じて以下で自動生成済みモデルをすべて確認できます。

::: oqtopus_client.models.generated
