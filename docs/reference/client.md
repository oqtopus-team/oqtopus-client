# `oqtopus_client.client`

## Initialization

### Default profile (`from_file`)

```python
from oqtopus_client import OqtopusClient

client = OqtopusClient()
```

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

client = OqtopusClient(OqtopusConfig.from_file(section="oqtopus-dev", path="~/.config/oqtopus/config.ini"))
```

### From environment variables

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
```

::: oqtopus_client.client.OqtopusClient
