# oqtopus-client

Python SDK for the OQTOPUS Cloud User API.

## Overview

`oqtopus-client` provides a typed Python interface for the OQTOPUS Cloud User API.

- Submit and manage jobs from Python.
- Use generated Pydantic models for request and response validation.
- Authenticate with config profiles, environment variables, or explicit `OqtopusConfig`.
- Use helper APIs such as `OqtopusJobSpec` and `run_*` to reduce boilerplate.
- Rely on built-in retry and typed job result wrappers for stable operation.

## Installation

```bash
pip install oqtopus-client
```

For local development, see [Setup Development Environment](./docs/developer_guidelines/setup.md).

## Documentation

- [Documentation Home](./docs/en/index.md)
- [Getting Started](./docs/en/quickstart.md)
- [Examples](./docs/en/examples.md)
- [API Reference](./docs/en/api.md)

## Developer Guidelines

- [Development Flow](./docs/developer_guidelines/development_flow.md)
- [Setup Development Environment](./docs/developer_guidelines/setup.md)
- [How to Contribute](./docs/CONTRIBUTING.md)
- [Code of Conduct](https://github.com/oqtopus-team/.github/blob/main/CODE_OF_CONDUCT.md)
- [Security](https://github.com/oqtopus-team/.github/blob/main/SECURITY.md)
