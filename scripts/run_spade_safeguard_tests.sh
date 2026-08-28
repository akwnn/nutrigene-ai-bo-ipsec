#!/bin/zsh
# SPADE integration safeguards — run before REGISTERED development or after integration commits.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${SPADE_PYTHON:-$ROOT/.venv/bin/python}"

echo "== git clean check (REGISTERED) =="
"$PY" -c "import sys;from pathlib import Path;sys.path.insert(0,'scripts');import run_spade_development as r;dirty=r.git_state(Path('.'))[1];sys.exit(0 if not dirty else 1)"

echo "== protocol / scoring alignment =="
"$PY" -m pytest tests/test_spade_development.py::test_development_runner_reliability_matches_frozen_protocol_and_scoring -q

echo "== Joseph integration imports =="
"$PY" -m pytest tests/test_hypermix.py tests/test_multiround.py tests/test_sur.py tests/test_certificate_straddle.py tests/test_certificate_targeted_policy.py -q

echo "== SPADE manufacturing core =="
"$PY" -m pytest tests/test_spade_study.py tests/test_spade_development.py tests/test_spade_lockbox.py -q

echo "SAFEGUARD PASS $(date -u +%Y-%m-%dT%H:%M:%SZ)"
