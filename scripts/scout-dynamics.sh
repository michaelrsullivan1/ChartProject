#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${REPO_ROOT}/.venv/bin/python3" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" backend/scripts/analysis/find_interesting_dynamics.py "$@"
