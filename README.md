![OQTOPUS logo](./docs/asset/oqtopus-logo.png)

# oqtopus-client

Python client library for the OQTOPUS Cloud User API.

## Overview

`oqtopus-client` is a Python SDK for the OQTOPUS Cloud User API.

It is designed for users who want to submit, monitor, and retrieve quantum jobs
from Python without handling raw HTTP requests or generated API models directly.
The library provides a synchronous public API for ease of use, while handling
network communication asynchronously inside the client.

The SDK covers both low-level API access and higher-level convenience helpers.
You can work directly with typed request/response models when you need explicit
control, or use helpers such as `OqtopusJobSpec`, `run_*`, `wait`, and typed
result wrappers for a more concise workflow.

## Features

- Typed Python access to the OQTOPUS Cloud User API.
- Synchronous public client API with asynchronous internal HTTP handling.
- Job submission helpers for sampling, estimation, multi-manual, and SSE (Server-Side Execution)
  workflows.
- Job lifecycle operations such as submit, wait, status check, refresh, cancel,
  and delete.
- Typed job result helpers for sampling, estimation, multi-manual, and SSE
  result handling.
- Generated Pydantic models for request and response validation.
- Built-in retry and backoff controls for more stable API access.
- Example scripts covering basic usage, parallel submission, and integration
  workflows.

## Documentation

- [Documentation Home](./docs/index.md)
- [Getting Started](./docs/usage/getting_started.md)
- [Examples](./docs/usage/examples.md)
- [GitHub Examples Directory](https://github.com/oqtopus-team/oqtopus-client/tree/main/examples)

## Developer Guidelines

- [Development Flow](./docs/developer_guidelines/development_flow.md)
- [Setup Development Environment](./docs/developer_guidelines/setup.md)
- [How to Contribute](./docs/CONTRIBUTING.md)
- [Code of Conduct](https://github.com/oqtopus-team/.github/blob/main/CODE_OF_CONDUCT.md)
- [Security](https://github.com/oqtopus-team/.github/blob/main/SECURITY.md)

## Citation

You can use the DOI to cite OQTOPUS in your research.

[![DOI](https://zenodo.org/badge/943222082.svg)](https://zenodo.org/badge/latestdoi/943222082)

Citation information is also available in the [CITATION](https://github.com/oqtopus-team/oqtopus-client/blob/main/CITATION.cff) file.

## Contact

You can contact us by creating an issue in this repository or by email:

- [oqtopus-team[at]googlegroups.com](mailto:oqtopus-team[at]googlegroups.com)

## License

`oqtopus-client` is released under the [Apache License 2.0](https://github.com/oqtopus-team/oqtopus-client/blob/main/LICENSE).
