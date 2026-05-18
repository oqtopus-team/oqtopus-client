![OQTOPUS logo](https://raw.githubusercontent.com/oqtopus-team/oqtopus-client/main/docs/asset/oqtopus-logo.png)

# OQTOPUS Client

[![CI](https://github.com/oqtopus-team/oqtopus-client/actions/workflows/ci.yaml/badge.svg)](https://github.com/oqtopus-team/oqtopus-client/actions/workflows/ci.yaml)
[![pypi version](https://img.shields.io/pypi/v/oqtopus-client.svg)](https://pypi.org/project/oqtopus-client/)
[![Python versions](https://img.shields.io/pypi/pyversions/oqtopus-client.svg)](https://pypi.org/project/oqtopus-client/)
[![GitHub release](https://img.shields.io/github/v/release/oqtopus-team/oqtopus-client)](https://github.com/oqtopus-team/oqtopus-client/releases)
[![Documentation Status](https://readthedocs.org/projects/oqtopus-client/badge/?version=latest)](https://oqtopus-client.readthedocs.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![slack](https://img.shields.io/badge/slack-OQTOPUS-pink.svg?logo=slack&style=plastic)](https://join.slack.com/t/oqtopus/shared_invite/zt-3bpjb7yc3-Vg8IYSMY1m5wV3DR~TMSnw)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20155552.svg)](https://doi.org/10.5281/zenodo.20155552)

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

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20155552.svg)](https://doi.org/10.5281/zenodo.20155552)

Citation information is also available in the [CITATION](https://github.com/oqtopus-team/oqtopus-client/blob/main/CITATION.cff) file.

## Contact

You can contact us by creating an issue in this repository or by email:

- [oqtopus-team[at]googlegroups.com](mailto:oqtopus-team[at]googlegroups.com)

## License

OQTOPUS Client is released under the [Apache License 2.0](https://github.com/oqtopus-team/oqtopus-client/blob/main/LICENSE).
