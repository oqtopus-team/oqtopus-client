# Getting Started

## Install

```bash
pip install oqtopus-client
```

The core client works without depending on other quantum software SDKs.

## Basic usage

You can start with `OqtopusJobSpec` helper methods and run jobs without manually constructing generated OpenAPI models.

```python
from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

client = OqtopusClient(OqtopusConfig(base_url="https://api.example.com", api_token="<token>"))
req = OqtopusJobSpec.sampling(
    device_id="Kawasaki",
    program="OPENQASM 3; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;",
    shots=1000,
)
result = client.run_sampling(req, timeout=300.0)
print(result.job_id)
print(result.get_counts())
```

## Authentication via environment variables

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN="<token>"
```

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(OqtopusConfig.from_env())
print(client.list_devices())
```

You can also load token from file:

```python
from oqtopus_client import OqtopusClient, OqtopusConfig

client = OqtopusClient(
    OqtopusConfig(
        base_url="https://api.example.com",
        api_token_file="~/.config/oqtopus/token.json",
    )
)
print(client.list_devices())
```

Or via environment variable:

```bash
export OQTOPUS_BASE_URL="https://api.example.com"
export OQTOPUS_API_TOKEN_FILE="~/.config/oqtopus/token.json"
```

## Language-specific guides

- [English quickstart](../en/quickstart.md)
