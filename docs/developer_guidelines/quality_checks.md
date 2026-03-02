# Quality Checks

Run the following checks from the repository root.

## Lint

```bash
make lint
```

- Runs `uv run --extra dev ruff check`.
- Rule configuration is managed in `pyproject.toml` under `[tool.ruff]`.

## Type check

```bash
make typecheck
```

- Runs `uv run --extra dev mypy`.
- Target paths and excludes are managed in `pyproject.toml` under `[tool.mypy]`.

## Test

```bash
make test
```

- Runs `uv run --extra dev pytest`.
- Test options are managed in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Combined check

```bash
make check
```

- Executes `lint`, `typecheck`, and `test` in order.

## Documentation checks

```bash
make docs
make docs-serve
```

- `make docs` builds docs with strict checks.
- `make docs-serve` runs local preview server.
