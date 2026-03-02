# Setup Development Environment

## Prerequisites

- [Python](https://www.python.org/downloads/) >= 3.10
- [uv](https://docs.astral.sh/uv/) >= 0.5
- [Docker](https://docs.docker.com/get-docker/) (required for `make generate-models`)

## Clone

```bash
git clone https://github.com/oqtopus-team/oqtopus-client.git
cd oqtopus-client
```

## Install dependencies

```bash
uv sync --extra dev
```

## Generate API models from OpenAPI

### Source of truth

- `spec/openapi.yaml` is the source-of-truth for generated API client models.
- Do not manually edit generated files under `src/oqtopus_client/rest/`.

### Update flow

```bash
make download-oas
make generate-models
```

If needed, you can override the source URL and output destination.

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/main/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/rest
```

Notes:

- `make generate-models` uses Docker (`openapitools/openapi-generator-cli`) internally.
- Keep generated diffs minimal and aligned with intended OAS changes.

## Validate changes

Run the following checks from the repository root.

### Lint

```bash
make lint
```

- Runs `uv run --extra dev ruff check`.
- Rule configuration is managed in `pyproject.toml` under `[tool.ruff]`.

### Type check

```bash
make typecheck
```

- Runs `uv run --extra dev mypy`.
- Target paths and excludes are managed in `pyproject.toml` under `[tool.mypy]`.

### Test

```bash
make test
```

- Runs `uv run --extra dev pytest`.
- Test options are managed in `pyproject.toml` under `[tool.pytest.ini_options]`.

### Combined check

```bash
make check
```

- Executes `lint`, `typecheck`, and `test` in order.

### Documentation checks

```bash
make docs
make docs-serve
```

- `make docs` builds docs with strict checks.
- `make docs-serve` runs local preview server.
