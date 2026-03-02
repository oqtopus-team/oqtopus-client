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

```bash
make download-oas
make generate-models
```

If needed, you can override the source URL and output destination.

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/main/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/rest
```

## Validate changes

Run commands from the repository root.

### Lint

```bash
make lint
```

### Type check

```bash
make typecheck
```

### Test

```bash
make test
```

### Run all checks

```bash
make check
```

## Build documentation

```bash
make docs
```

Local preview:

```bash
make docs-serve
```
