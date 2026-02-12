# Examples

`examples/` は Python スクリプト (`*.py`) で統一しています。

## Python examples

- `get_devices.py`
- `run_sampling.py`
- `run_estimation.py`
- `run_multi_manual.py`
- `run_sse_file.py`
- `run_sampling_quri_parts.py`
- `run_sampling_qiskit.py`
- `submit_jobs_parallel.py` (`OqtopusClient.submit_jobs` / `wait_for_jobs`)
- `run_job_generic.py` (`OqtopusClient.run_job`)
- `job_handle_lifecycle.py` (`OqtopusJobHandle` methods)
- `run_jobs_batch.py` (`run_jobs_batch`)
- `wait_and_delete_job.py` (`wait_for_job`, `delete_job`)
- `manage_api_token.py` (`create_api_token`, `delete_api_token`)
- `get_announcement_detail.py` (`get_announcements_list`, `get_announcement`)
- `init_client_from_env.py` (`from_env`, `set_api_token`, client config attributes)
- `list_devices_and_jobs.py` (`list_devices`, `get_device`, `list_jobs`)
- `get_user_and_status.py` (`get_current_user`, `get_announcements_list`, `get_api_token_status`)
- `get_job.py`
- `cancel_job.py`

実行:

```bash
python examples/get_devices.py
```

基本の書き方は以下です。

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

with OqtopusClient(OqtopusConfig.from_file("oqtopus-dev")) as client:
    finished_job = client.run_job(request, timeout=300.0)
    print(finished_job.status)
```

セクション名・ファイルパスを変える場合は、各スクリプト内の
`OQTOPUS_CONFIG_SECTION` と `OQTOPUS_CONFIG_PATH` 環境変数で切り替えできます。

`run_sse_file.py` は `examples/userprogram.py` を SSE ジョブとして送信し、
実行後に SSE ログを既定ではメモリ内で扱い、必要時のみ明示指定で保存して内容を表示します。

## Utilities

結果整形:

```python
from oqtopus_client import normalize_sampling_result

normalized = normalize_sampling_result(finished_job.job_info.result.sampling)
print(normalized["counts"])
```
