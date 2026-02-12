# Setup Development Environment

## Prerequisites

- Python >= 3.10
- `uv` (recommended) or `pip`

## Clone

```bash
git clone https://github.com/oqtopus-team/oqtopus-client.git
cd oqtopus-client
```

## Install dependencies

```bash
uv sync
```

or

```bash
pip install -e ".[dev]"
```

## Run checks

```bash
make lint
make typecheck
make test
```

## Build docs

```bash
make docs
```
