# `oqtopus_client.client`

## Initialization

### Direct constructor

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(
    OqtopusConfig(
        base_url="https://api.example.com",
        api_token="<token>",
        timeout=30.0,
    )
)
```

### From profile file

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_file(section="oqtopus-dev", path="~/.oqtopus"))
```

### From environment variables

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
```

::: oqtopus_client.client.OqtopusClient
