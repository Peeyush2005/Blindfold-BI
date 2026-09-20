#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "  Blindfold BI: Local CI Validation Suite"
echo "=========================================================="

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "--> [1/5] Checking repository hygiene & read-only guard..."
# Zero GraphQL mutations allowed in backend/app
MUTATION_COUNT=$(grep -rn "mutation" backend/app 2>/dev/null | wc -l || true)
if [ "$MUTATION_COUNT" -gt 0 ]; then
  echo "FAIL: Found $MUTATION_COUNT occurrences of 'mutation' in backend/app!"
  grep -rn "mutation" backend/app
  exit 1
fi
echo "      Passed: Zero mutations detected in backend/app."

# Verify no xlsx files outside fixtures
XLSX_OUTSIDE=$(find . -name "*.xlsx" -not -path "*/tests/fixtures/*" -not -path "*/.git/*" -not -path "*/data/*" 2>/dev/null || true)
if [ -n "$XLSX_OUTSIDE" ]; then
  echo "WARN: Found xlsx files outside tests/fixtures/ and data/: $XLSX_OUTSIDE"
fi

echo "--> [2/5] Preparing Python virtual environment..."
VENV_DIR="${REPO_ROOT}/.venv_ci"
if [ ! -d "$VENV_DIR" ]; then
  echo "      Creating virtual environment at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "--> [3/5] Installing backend dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt
pip install --quiet pytest

echo "--> [4/5] Running backend test suite with pytest..."
cd "$REPO_ROOT/backend"
python -m pytest -v tests/

echo "--> [5/5] Building frontend bundle..."
cd "$REPO_ROOT/frontend"
npm install --silent
npm run build

echo "=========================================================="
echo "  CI SUCCESS: All backend tests passed & frontend built cleanly!"
echo "=========================================================="
