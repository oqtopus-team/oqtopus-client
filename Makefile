SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: download-oas generate-models test lint typecheck check docs docs-serve
DOCS_ADDR ?= 127.0.0.1:8000

download-oas:
	$(MAKE) -C spec download-oas

generate-models:
	$(MAKE) -C spec generate-models

test:
	@uv run pytest

lint:
	@uv run ruff check

typecheck:
	@uv run mypy

check: lint typecheck test

docs:
	@uv run mkdocs build --strict

docs-serve:
	@uv run mkdocs serve -a $(DOCS_ADDR)
