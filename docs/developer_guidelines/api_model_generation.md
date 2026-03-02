# API Model Generation

## Source of truth

- `spec/openapi.yaml` is the source-of-truth for generated API client models.
- Do not manually edit generated files under `src/oqtopus_client/models/generated/`.

## Update flow

1. Download latest OAS:

```bash
make download-oas
```

2. Generate models from OAS:

```bash
make generate-models
```

3. Run checks:

```bash
make lint
make typecheck
make test
```

## Optional overrides

Use these when validating against a custom OAS URL or a local file.

```bash
make -C spec download-oas OAS_URL=https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/main/backend/oas/user/openapi.yaml
make -C spec generate-models OAS_FILE=openapi.yaml MODEL_OUTPUT_DIR=../src/oqtopus_client/models
```

## Notes

- `make generate-models` uses Docker (`openapitools/openapi-generator-cli`) internally.
- Keep generated diffs minimal and aligned with intended OAS changes.
