SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: download-oas generate-models test lint typecheck check docs docs-serve
DOCS_ADDR ?= 127.0.0.1:8000

download-oas:
	$(MAKE) -C spec download-oas

generate-models:
	$(MAKE) -C spec generate-models

test:
	@uv run --extra dev pytest

lint:
	@uv run --extra dev ruff check

typecheck:
	@uv run --extra dev mypy

check: lint typecheck test

docs:
	@uv run --extra dev mkdocs build --strict

docs-serve:
	@uv run --extra dev mkdocs serve -a $(DOCS_ADDR)
