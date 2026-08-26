#!/bin/zsh
set -euo pipefail
cd "/Users/alanakwan/Personal Projects/nutrigene-ai-bo-ipsec/.worktrees/spade-campaign"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
PY="/Users/alanakwan/Personal Projects/nutrigene-ai-bo-ipsec/.venv/bin/python"
LOG=/tmp/spade-dev-run/pipeline.log
echo "PIPELINE_START $(date -Iseconds)" | tee -a "$LOG"

ensure_clean() {
  $PY - <<'PY' | tee -a "$LOG"
import sys
from pathlib import Path
sys.path.insert(0,'scripts')
import run_spade_development as r
commit, dirty = r.git_state(Path('.'))
print(f"git_state commit={commit[:12]} dirty={dirty}")
if dirty:
    raise SystemExit("REFUSING dirty tree")
PY
}

wait_for_complete() {
  local fam=$1
  local man="results/spade-development-${fam}-000-050.jsonl.gz.manifest.json"
  local resume="results/spade-development-${fam}-000-050.jsonl.gz.resume.json"
  local logf="results/spade-development-${fam}-000-050.log"
  while true; do
    if [[ -f "$man" ]]; then
      local shard_status
      shard_status=$($PY -c "import json;print(json.load(open('$man'))['status'])")
      if [[ "$shard_status" == "COMPLETE" ]]; then
        echo "${fam}_COMPLETE $(date -Iseconds)" | tee -a "$LOG"
        return 0
      fi
    fi
    if ! pgrep -f "run_spade_development.py --family ${fam}" >/dev/null; then
      local rows=0
      if [[ -f "$resume" ]]; then
        rows=$($PY -c "import json;print(json.load(open('$resume'))['row_count'])")
      fi
      echo "${fam}_DEAD rows=$rows $(date -Iseconds) — resuming" | tee -a "$LOG"
      ensure_clean
      $PY -u scripts/run_spade_development.py --family "$fam" --start 0 --stop 50 --out "results/spade-development-${fam}-000-050.jsonl.gz" >>"$logf" 2>&1 &
      sleep 30
      continue
    fi
    local rows='?'
    if [[ -f "$resume" ]]; then
      rows=$($PY -c "import json;print(json.load(open('$resume'))['row_count'])")
    fi
    echo "WAIT_${fam} rows=$rows $(date -Iseconds)" | tee -a "$LOG"
    sleep 60
  done
}

# Levy already complete — still call wait (immediate return)
wait_for_complete levy
ensure_clean

if [[ ! -f results/spade-development-hill-000-001.jsonl.gz.manifest.json ]]; then
  echo "HILL_000_001_START $(date -Iseconds)" | tee -a "$LOG"
  $PY -u scripts/run_spade_development.py --family hill --start 0 --stop 1 --out results/spade-development-hill-000-001.jsonl.gz >> results/spade-development-hill-000-001.log 2>&1
  echo "HILL_000_001_DONE $(date -Iseconds)" | tee -a "$LOG"
fi

echo "HILL_MERGE_START $(date -Iseconds)" | tee -a "$LOG"
$PY scripts/merge_spade_development_shards.py \
  --family hill \
  --manifest results/spade-development-hill-000-001.jsonl.gz.manifest.json \
  --manifest results/spade-development-hill-001-015.jsonl.gz.manifest.json \
  --manifest results/spade-development-hill-015-030.jsonl.gz.manifest.json \
  --manifest results/spade-development-hill-030-050.jsonl.gz.manifest.json \
  --out results/spade-development-hill-000-050.jsonl.gz | tee -a /tmp/spade-dev-run/hill_merge.out
echo "HILL_MERGE_DONE $(date -Iseconds)" | tee -a "$LOG"

ensure_clean
if [[ ! -f results/spade-development-rosenbrock-000-050.jsonl.gz.manifest.json ]]; then
  echo "ROSEN_START $(date -Iseconds)" | tee -a "$LOG"
  $PY -u scripts/run_spade_development.py --family rosenbrock --start 0 --stop 50 --out results/spade-development-rosenbrock-000-050.jsonl.gz >> results/spade-development-rosenbrock-000-050.log 2>&1
  echo "ROSEN_DONE $(date -Iseconds)" | tee -a "$LOG"
fi

echo "ALL_DEV_FAMILIES_READY $(date -Iseconds)" | tee -a "$LOG"
touch /tmp/spade-dev-run/DEV_READY
echo "DEV_READY $(date -Iseconds)" | tee -a "$LOG"
