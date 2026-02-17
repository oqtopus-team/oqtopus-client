SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: download-oas generate-models test lint typecheck check docs docs-serve
DOCS_ADDR ?= 127.0.0.1:8000

download-oas:
	$(MAKE) -C spec download-oas

generate-models:
	$(MAKE) -C spec generate-models

test:
	PYTHONPATH=src pytest

lint:
	@if python3 -c "import ruff" >/dev/null 2>&1; then \
		python3 -m ruff check src tests scripts examples; \
	elif command -v uv >/dev/null 2>&1; then \
		uv run --extra dev ruff check src tests scripts examples; \
	else \
		echo "ruff is not installed. Run: pip install -e '.[dev]'"; \
		exit 1; \
	fi

typecheck:
	@if python3 -c "import mypy" >/dev/null 2>&1; then \
		python3 -m mypy; \
	elif command -v uv >/dev/null 2>&1; then \
		uv run --extra dev mypy; \
	else \
		echo "mypy is not installed. Run: pip install -e '.[dev]'"; \
		exit 1; \
	fi

check: lint typecheck test

docs:
	@if [ -x .venv/bin/python ] && .venv/bin/python -c "import mkdocs, mkdocstrings, mkdocstrings_handlers.python" >/dev/null 2>&1; then \
		PYTHONPATH=src .venv/bin/python -m mkdocs build --strict; \
	elif python3 -c "import mkdocs, mkdocstrings, mkdocstrings_handlers.python" >/dev/null 2>&1; then \
		PYTHONPATH=src python3 -m mkdocs build --strict; \
	elif command -v uv >/dev/null 2>&1; then \
		uv run --extra dev mkdocs build --strict; \
	else \
		echo "docs dependencies are missing. Run: pip install -e '.[dev]'"; \
		exit 1; \
	fi

docs-serve:
	@if [ -x .venv/bin/python ] && .venv/bin/python -c "import mkdocs, mkdocstrings, mkdocstrings_handlers.python" >/dev/null 2>&1; then \
		PYTHONPATH=src .venv/bin/python -m mkdocs serve -a $(DOCS_ADDR); \
	elif python3 -c "import mkdocs, mkdocstrings, mkdocstrings_handlers.python" >/dev/null 2>&1; then \
		PYTHONPATH=src python3 -m mkdocs serve -a $(DOCS_ADDR); \
	elif command -v uv >/dev/null 2>&1; then \
		uv run --extra dev mkdocs serve -a $(DOCS_ADDR); \
	else \
		echo "docs dependencies are missing. Run: pip install -e '.[dev]'"; \
		exit 1; \
	fi
