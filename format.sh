#!/usr/bin/env bash
set -eo pipefail

RUFF_VERSION=$(ruff --version | head -n 1 | awk '{print $2}')
MYPY_VERSION=$(mypy --version | awk '{print $2}')

echo "ruff ver $YAPF_VERSION"
echo "mypy ver $MYPY_VERSION"

# Run mypy
echo 'Konduktor mypy:'
mypy $(cat tests/mypy_files.txt)

# Run ruff
echo 'Konduktor ruff:'
ruff check --fix konduktor tests
ruff format konduktor tests
