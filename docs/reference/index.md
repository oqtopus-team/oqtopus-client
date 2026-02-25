# API Reference

API reference is organized by module.

## Core Modules

- [`OqtopusClient`](client.md): Main HTTP client and endpoint wrappers.
- [`OqtopusConfig`](config.md): Client configuration loader and profile/env utilities.
- [`OqtopusJobSpec`](job_spec.md): Unified thin input wrapper for concise job submissions.
- [`OqtopusEstimationOperator`](estimation_operator.md): Typed operator wrapper for estimation inputs.
- [`OqtopusJobResult` family](job_results.md): Typed result objects (sampling/estimation/multi_manual/sse).
- [`device` wrapper](device.md): Typed wrapper for device information.
- [`UserApiError` / `ResponseValidationError`](errors.md): SDK exception classes.
- [`models`](models.md): Generated Pydantic models.

## Notes

- Helper classes/functions are listed first, then lower-level modules.
- Public API is documented via `mkdocstrings` from `src/oqtopus_client`.
