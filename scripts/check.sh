#!/usr/bin/env sh
set -eu
uv sync --locked
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
