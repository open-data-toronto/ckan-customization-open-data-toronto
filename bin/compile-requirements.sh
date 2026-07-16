#!/usr/bin/env bash
# Regenerate requirements.txt from requirements.in.
# Run from anywhere inside the opendata_ckan repo:
#
#   bin/compile-requirements.sh
#
# Output: opendata_ckan/requirements.txt (commit this file)
# Source: opendata_ckan/requirements.in  (edit this file to change deps)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

if command -v uv &>/dev/null; then
  COMPILE="uv pip compile"
elif command -v pip-compile &>/dev/null; then
  COMPILE="pip-compile"
else
  echo "Neither uv nor pip-compile found. Install one of:"
  echo "  uv:        curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  pip-tools: pip install pip-tools"
  exit 1
fi

echo "Compiling $REPO_DIR/requirements.txt ..."

$COMPILE \
  --python-version 3.9 \
  --output-file "$REPO_DIR/requirements.txt" \
  --annotation-style line \
  --strip-extras \
  "$REPO_DIR/requirements.in"

echo "Done. Commit requirements.txt."
