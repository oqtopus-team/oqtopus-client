# oqtopus-client

Python client library for the OQTOPUS Cloud User API.

This documentation auto-generates API references from docstrings in `src/oqtopus_client`.

## Key Features

- Operate User API endpoints via Python methods.
- Type-safe request/response handling using Pydantic models generated from downloaded OpenAPI schema.
- Supports configuration via the default `config.ini` profile, named profiles, environment variables, and explicit `OqtopusConfig`.
- Core client usage does not require any other quantum software SDK.
- OpenAPI-generated models are used internally, while helper APIs such as `OqtopusJobSpec` and `run_*` reduce boilerplate.
- Internal HTTP communication is asynchronous, with an easy-to-use synchronous public API.
- Built-in retry/backoff controls and typed result wrappers support stable operation.

## Quick Links

- [Getting Started](usage/getting_started.md)
- [API Reference](reference/API_reference.md)
- [Examples](usage/examples.md)
- [Developer Guidelines](developer_guidelines/development_flow.md)
