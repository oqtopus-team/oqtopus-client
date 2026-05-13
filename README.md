![OQTOPUS logo](https://raw.githubusercontent.com/oqtopus-team/oqtopus-client/main/docs/asset/oqtopus-logo.png)

# OQTOPUS Client

Python client library for the OQTOPUS Cloud User API.

## Overview

OQTOPUS Client is a Python SDK for the OQTOPUS Cloud User API.

It is designed for users who want to submit, monitor, and retrieve quantum jobs
from Python without handling raw HTTP requests directly. The library provides a
synchronous public API for ease of use, while handling network communication
asynchronously inside the client.

The SDK covers both low-level API access and higher-level convenience helpers.
You can work directly with typed request/response models when you need explicit
control, or use helpers such as `OqtopusJobSpec`, `run_*`, and typed result
wrappers for a more concise workflow.

## Features

- Typed Python access to the OQTOPUS Cloud User API.
- Job submission helpers for sampling, estimation, multi-manual, and SSE (Server-Side Execution)
  workflows.
- Job lifecycle operations such as submit, wait, status, cancel, and delete.
- Typed result wrappers and generated Pydantic models.
- Configuration via config files, environment variables, or explicit
  `OqtopusConfig`.
- Built-in retry and backoff controls.

## Documentation

- [Documentation Home](https://oqtopus-client.readthedocs.io/)

## Citation

You can use the DOI to cite OQTOPUS in your research.

[![DOI](https://zenodo.org/badge/1156029183.svg)](https://zenodo.org/badge/latestdoi/1156029183)

Citation information is also available in the [CITATION](https://github.com/oqtopus-team/oqtopus-client/blob/main/CITATION.cff) file.

## Contact

You can contact us by creating an issue in this repository or by email:

- [oqtopus-team[at]googlegroups.com](mailto:oqtopus-team[at]googlegroups.com)

## License

OQTOPUS Client is released under the [Apache License 2.0](https://github.com/oqtopus-team/oqtopus-client/blob/main/LICENSE).
