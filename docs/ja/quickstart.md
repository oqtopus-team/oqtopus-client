# Quickstart

## インストール

```bash
pip install oqtopus-client
```

ローカル開発時は以下のように利用できます。

```bash
pip install -e .
```

## 認証

`OqtopusClient` は以下のいずれかで Bearer トークンを設定できます。

- `api_token`: トークン文字列を直接指定
- `api_token_file`: ファイルから読み込み

`api_token_file` は次の形式をサポートします。

```text
<plain token>
```

```json
{"api_token_secret":"<token>"}
```

## 最小例

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    devices = client.list_devices()
    req = models.JobsSubmitJobRequest(
        device_id="Kawasaki",
        job_type=models.JobsJobType.SAMPLING,
        shots=1000,
        job_info=models.JobsSubmitJobInfo(
            program=["OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;"]
        ),
    )
    job = client.submit_job(req)
    print(job.job_id)
```

## 環境変数から初期化

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_env()) as client:
    print(client.list_devices())
```

必要なら以下も利用できます。

- `OQTOPUS_API_TOKEN_FILE`: トークンファイルパス
- `default_headers`: 共通ヘッダ追加
- `user_agent`: User-Agent 上書き

## ジョブ実行の高レベルヘルパー

`submit` + `wait` を1回で完了させるには `OqtopusClient.run_job()` が使えます。

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, models

req = models.JobsSubmitJobRequest(
    device_id="Kawasaki",
    job_type=models.JobsJobType.SAMPLING,
    shots=100,
    job_info=models.JobsSubmitJobInfo(program=["OPENQASM 3; qubit[1] q;"]),
)

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    final_job = client.run_job(req, timeout=300.0)
    print(final_job.status)
```

`job_type` ごとのショートカットも使えます（不一致時は `ValueError`）。

```python
final_sampling = client.run_sampling(sampling_req)
final_estimation = client.run_estimation(estimation_req)
final_manual = client.run_multi_manual(multi_manual_req)
final_sse = client.run_sse(sse_req)
```

提出済みジョブを段階的に扱う場合は `OqtopusJobHandle` が使えます。

```python
from oqtopus_client import OqtopusJobHandle

submitted_job = client.submit_job(req)
job = OqtopusJobHandle(client, submitted_job.job_id)
print(job.job_id)
print(job.status())
final_job = job.wait(interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
```

## 言語

- [English](../en/quickstart.md)
