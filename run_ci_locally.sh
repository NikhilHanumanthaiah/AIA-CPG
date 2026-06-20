#!/bin/bash
# Exit immediately if any command exits with a non-zero status
set -e

echo "=== Running Local CI Checks ==="

# 1. Format checks
echo "Running Black formatting check..."
black --check .

echo "Running isort import ordering check..."
isort --check-only .

# 2. Run test suite
echo "Running Pytest suite..."
pytest

echo "=== All Checks Passed Successfully! ==="
