# Setup Development Environment

## Prerequisites

- Python >= 3.10
- `uv`

## Clone

```bash
git clone https://github.com/oqtopus-team/oqtopus-client.git
cd oqtopus-client
```

## Install dependencies

```bash
uv sync --extra dev
```

## OAS and generated models

```bash
make download-oas
make generate-models
```

If needed, you can override the source URL and output destination.

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/main/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/models
```

## Run checks

```bash
make lint
make typecheck
make test
make check
```

## Build docs

```bash
make docs
make docs-serve
```
