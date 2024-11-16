#!/usr/bin/env bash
set -eo pipefail

RUFF_VERSION=$(poetry run ruff --version | head -n 1 | awk '{print $2}')
MYPY_VERSION=$(poetry run mypy --version | awk '{print $2}')

echo "ruff ver $RUFF_VERSION"
echo "mypy ver $MYPY_VERSION"

# Run mypy
echo 'Konduktor mypy:'
poetry run mypy $(cat tests/mypy_files.txt)

# Run ruff
echo 'Konduktor ruff:'
poetry run ruff check --fix konduktor tests
poetry run ruff format konduktor tests
