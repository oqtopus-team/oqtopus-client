![OQTOPUS logo](./asset/oqtopus-logo.png)

# oqtopus-client

Python client library for the OQTOPUS Cloud User API.

## Overview

**`oqtopus-client`** is a Python SDK for the OQTOPUS Cloud User API.

It is designed for users who want to submit, monitor, and retrieve quantum jobs
from Python without handling raw HTTP requests directly. The public API is
primarily synchronous for ease of use, while network communication is handled
asynchronously inside the client.

The SDK includes two layers:

- a higher-level SDK surface for common workflows such as sampling, estimation,
  multi-manual jobs, and SSE jobs
- a generated low-level OpenAPI client for direct access to API models and
  endpoint bindings

Use this documentation site when you want installation help, end-to-end usage
examples, API reference pages, or contributor guidance.

## Features

- Typed Python access to the OQTOPUS Cloud User API
- Convenience helpers such as `OqtopusJobSpec`, `run_*`, and typed result
  wrappers
- Job lifecycle operations such as submit, wait, status, cancel, and delete
- Parsed device metadata through `OqtopusDevice`
- Generated OpenAPI models and low-level client bindings under
  `oqtopus_client.rest`
- Configuration via config files, environment variables, or explicit
  `OqtopusConfig`
- Retry and backoff controls for retryable requests

## Usage

- [Getting Started](./usage/getting_started.md): installation, configuration,
  first job submission, and result handling
- [Examples](./usage/examples.md): runnable examples and common usage patterns

## API Reference

- [API Reference Overview](./reference/index.md): entry point for all reference
  documentation
- [SDK Reference](./reference/sdk/oqtopus_client/index.md): high-level SDK
  objects such as `OqtopusClient`, `OqtopusConfig`, job specs, and typed results
- [Generated OpenAPI Reference](./reference/generated/oqtopus_client/rest/index.md):
  generated API classes, transport helpers, and OpenAPI models

## Developer Guidelines

- [Development Flow](./developer_guidelines/development_flow.md)
- [Setup Development Environment](./developer_guidelines/setup.md)
- [How to Contribute](./CONTRIBUTING.md)
- [Code of Conduct](https://github.com/oqtopus-team/.github/blob/main/CODE_OF_CONDUCT.md)
- [Security](https://github.com/oqtopus-team/.github/blob/main/SECURITY.md)

## Citation

You can use the DOI to cite OQTOPUS in your research.

[![DOI](https://zenodo.org/badge/943222082.svg)](https://zenodo.org/badge/latestdoi/943222082)

Citation information is also available in the
[CITATION](https://github.com/oqtopus-team/oqtopus-client/blob/main/CITATION.cff)
file.

## Contact

You can contact us by creating an issue in this repository or by email:

- [oqtopus-team[at]googlegroups.com](mailto:oqtopus-team[at]googlegroups.com)

## License

`oqtopus-client` is released under the
[Apache License 2.0](https://github.com/oqtopus-team/oqtopus-client/blob/main/LICENSE).
