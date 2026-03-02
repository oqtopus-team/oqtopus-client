# `oqtopus_client`

## Initialization

### Direct constructor

```python
from oqtopus_client import OqtopusConfig

config = OqtopusConfig(
    base_url="https://api.example.com",
    api_token="<token>",
    timeout=30.0,
    retry_max_attempts=3,
    retry_backoff_seconds=0.2,
)
```

### From profile file

```python
from oqtopus_client import OqtopusConfig

config = OqtopusConfig.from_file(section="oqtopus-dev", path="~/.config/oqtopus/config.ini")
```

### From environment variables

```python
from oqtopus_client import OqtopusConfig

config = OqtopusConfig.from_env()
```

Required env var: `OQTOPUS_BASE_URL`  
Optional env var: `OQTOPUS_API_TOKEN`

::: oqtopus_client.OqtopusConfig
