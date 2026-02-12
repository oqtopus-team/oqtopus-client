# oqtopus-client

Python SDK for OQTOPUS Cloud User API.

This documentation auto-generates API references from docstrings in `src/oqtopus_client`.

## Key Features

- Operate User API endpoints via Python methods.
- Type-safe request/response handling using Pydantic models generated from `spec/openapi.yaml`.
- Supports both direct token string and token file authentication.
- Core client usage does not require any other quantum software SDK.
- OpenAPI-generated models are used internally, while helper APIs such as `OqtopusJobSpec` and `run_*` reduce boilerplate.
- Internal HTTP communication is asynchronous, with an easy-to-use synchronous public API.
- Built-in retry/backoff controls and typed result wrappers support stable operation.

## Quick Links

- [Quickstart](quickstart.md)
- [API Reference](api.md)
- [Models](models.md)
- [Examples](examples.md)

## Language

- [日本語版](../ja/index.md)
