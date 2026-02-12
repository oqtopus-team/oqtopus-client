# oqtopus-client

OQTOPUS Cloud User API 向けの Python SDK です。

## 使い方

```bash
make download-oas
make generate-models
```

必要なら生成元や出力先を上書きできます。

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/models/generated/models
```

```python
from oqtopus_client import OqtopusJobSpec, OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>")) as client:
    devices = client.list_devices()
    req = OqtopusJobSpec.sampling(
        device_id="Kawasaki",
        program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
        shots=1000,
    )
    final_job = client.run_sampling(req, interval=2.0, timeout=300.0)
    print(final_job.status)
```

環境変数から初期化する場合は `OqtopusConfig.from_env()` を使います。

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_env()) as client:
    print(client.list_devices())
```

再試行ポリシーは初期化引数で調整できます（既定: `GET/DELETE` を 429/5xx で再試行）。

```python
from oqtopus_client import OqtopusClient
from oqtopus_client import OqtopusConfig

with OqtopusClient(
    OqtopusConfig(
        base_url="https://api.example.com",
        api_token="<token>",
        retry_max_attempts=3,
        retry_backoff_seconds=0.2,
    ),
) as client:
    print(client.list_devices())
```

既定ヘッダの追加や `User-Agent` 上書きも可能です。

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(
    OqtopusConfig(base_url="https://api.example.com", api_token="<token>"),
    default_headers={"X-Trace-ID": "trace-123"},
    user_agent="my-app/1.0.0",
) as client:
    print(client.get_current_user())
```

## examples

`examples/` には Python スクリプトの実行例を用意しています。

- `get_devices.py`
- `run_sampling.py (run_sampling)`
- `run_estimation.py (run_estimation)`
- `run_multi_manual.py (run_multi_manual)`
- `run_sse_file.py (run_sse_file, SSEログは既定メモリ内処理。保存は `download_log(..., persist=True)` を明示指定)`
- `run_sampling_qiskit.py`
- `run_sampling_quri_parts.py`
- `submit_jobs_parallel.py (OqtopusClient.submit_jobs / wait_for_jobs)`
- `run_job_generic.py (OqtopusClient.run_job)`
- `job_handle_lifecycle.py (OqtopusJobHandle methods)`
- `run_jobs_batch.py (OqtopusClient.run_jobs_batch)`
- `wait_and_delete_job.py (wait_for_job / delete_job)`
- `manage_api_token.py (create_api_token / delete_api_token)`
- `get_announcement_detail.py (get_announcements_list / get_announcement)`
- `init_client_from_env.py (OqtopusConfig.from_env / set_api_token / client attributes)`
- `list_devices_and_jobs.py (list_devices / get_device / list_jobs)`
- `get_user_and_status.py (get_current_user / get_announcements_list / get_api_token_status)`
- `get_job.py`
- `cancel_job.py`

基本の書き方は以下です。

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_file("oqtopus-dev")) as client:
    print(client.list_devices())
```

実行例:

```bash
python examples/get_devices.py
```

IBM Qiskit 回路から submit する example は、以下の追加依存が必要です。

```bash
pip install qiskit
```

サンプリング結果の bitstring キーを整数キーへ変換するユーティリティも利用できます。

```python
from oqtopus_client import normalize_sampling_result

normalized = normalize_sampling_result(final_job.job_info.result.sampling)
print(normalized["counts"])
```

トークンファイルを排他更新するユーティリティも利用できます。

```python
from oqtopus_client import write_api_token_file

write_api_token_file("credentials/token.json", "new-token", as_json=True)
```

複数ジョブの submit/wait を並列化するヘルパークラスも用意しています。

```python
responses = client.submit_jobs([req1, req2], max_workers=2)
final_jobs = client.wait_for_jobs([r.job_id for r in responses], max_workers=2)
```

提出済みジョブを段階的に扱う場合は `OqtopusJobHandle` を使えます。

```python
from oqtopus_client import OqtopusJobHandle

submitted_job = client.submit_job(req)
job = OqtopusJobHandle(client, submitted_job.job_id)
print(job.status())
final_job = job.wait(interval=1.0, interval_backoff=1.2, max_interval=5.0, timeout=300.0)
print(final_job.status)
```

submit + wait をまとめたワンショット実行やバッチ実行ヘルパーも提供しています。

```python
final_job = client.run_job(req, timeout=300.0)
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

docstring から API ドキュメントを自動生成できます。

```bash
pip install -e ".[dev]"
```

```bash
make docs
```

ローカルプレビュー:

```bash
make docs-serve
```

## 構成

- `spec/openapi.yaml`: モデル生成元の OAS
- `spec/Makefile`: `download-oas`（最新版取得）と `openapi-generator` 実行
- `Makefile`: `spec/Makefile` のラッパー
- `docs/`: API / 利用方法ドキュメント
- `mkdocs.yml`: ドキュメント生成設定
- `src/oqtopus_client/models/generated/`: 生成済みモデル（openapi-generator出力）
- `src/oqtopus_client/client.py`: 生成モデルを利用する SDK クライアント
- `examples/`: SDK 利用例
- `tests/`: SDK テスト
