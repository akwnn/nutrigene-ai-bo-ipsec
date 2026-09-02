#!/bin/zsh
# Durable SPADE REGISTERED development supervisor.
# - Max 2 concurrent family workers (avoids OOM)
# - Resumes from *.resume.json after crashes
# - Backs up resume checkpoints under /tmp/spade-resume-backups
# - Runs LOFO selection when all five 000-050 shards are COMPLETE
# - Refuses to start workers if the git tree is dirty
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 PYTHONHASHSEED=0 CUDA_VISIBLE_DEVICES=

LOG=/tmp/spade-watchdog.log
HB=/tmp/spade-watchdog.heartbeat
BACKUP=/tmp/spade-resume-backups
LOCK=/tmp/spade-watchdog.lock
FAMILIES=(hill levy hartmann6 ackley rosenbrock)
MAX_CONCURRENT=2
POLL_SEC=60

mkdir -p "$BACKUP"
echo "watchdog start $(date -u +%Y-%m-%dT%H:%M:%SZ) pid=$$ commit=$(git rev-parse --short HEAD) root=$ROOT" >> "$LOG"

if [ -f "$LOCK" ]; then
  old=$(cat "$LOCK" 2>/dev/null || true)
  if [ -n "${old:-}" ] && kill -0 "$old" 2>/dev/null; then
    echo "another watchdog alive pid=$old; exit" >> "$LOG"
    exit 0
  fi
fi
echo $$ > "$LOCK"

is_complete() {
  local fam=$1 out="results/spade-development-${fam}-000-050.jsonl.gz"
  [[ -f "$out" && -f "${out}.manifest.json" ]]
}

row_count() {
  local fam=$1 r="results/spade-development-${fam}-000-050.jsonl.gz.resume.json"
  if [[ -f "$r" ]]; then
    python3 -c "import json;print(json.load(open('$r')).get('row_count',0))" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

worker_running() {
  pgrep -f "run_spade_development.py --family ${1} --start 0 --stop 50" >/dev/null
}

backup_resumes() {
  local ts min
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  min=${ts:10:2}
  for fam in $FAMILIES; do
    local r="results/spade-development-${fam}-000-050.jsonl.gz.resume.json"
    if [[ -f "$r" ]]; then
      cp -f "$r" "$BACKUP/${fam}.resume.json"
      if [[ "$min" == "00" || "$min" == "30" ]]; then
        cp -f "$r" "$BACKUP/${fam}.resume.${ts}.json"
        ls -1t "$BACKUP/${fam}.resume."*.json 2>/dev/null | tail -n +4 | while read -r old; do
          rm -f "$old"
        done
      fi
    fi
  done
  {
    echo "ts=$ts"
    for fam in $FAMILIES; do
      if is_complete "$fam"; then
        echo "$fam COMPLETE"
      else
        echo "$fam rows=$(row_count "$fam")/550 running=$(worker_running "$fam" && echo yes || echo no)"
      fi
    done
  } > "$BACKUP/status.txt"
}

tree_clean() {
  .venv/bin/python -c "import sys;from pathlib import Path;sys.path.insert(0,'scripts');import run_spade_development as r;import sys;sys.exit(0 if not r.git_state(Path('.'))[1] else 1)"
}

start_family() {
  local fam=$1 out="results/spade-development-${fam}-000-050.jsonl.gz"
  is_complete "$fam" && return 0
  worker_running "$fam" && return 0
  if ! tree_clean; then
    echo "REFUSE start $fam: dirty tree $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
    return 1
  fi
  echo "START $fam from_rows=$(row_count "$fam") $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
  # Disown so workers survive if this watchdog is restarted.
  .venv/bin/python -u scripts/run_spade_development.py \
    --family "$fam" --start 0 --stop 50 --out "$out" \
    > "/tmp/spade-full-${fam}.log" 2>&1 &
  disown $! 2>/dev/null || true
  echo "  pid $!" >> "$LOG"
}

count_running() {
  local n=0
  for fam in $FAMILIES; do
    worker_running "$fam" && n=$((n+1))
  done
  echo $n
}

all_complete() {
  for fam in $FAMILIES; do
    is_complete "$fam" || return 1
  done
  return 0
}

run_lofo() {
  echo "LOFO start $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
  .venv/bin/python -u scripts/select_spade_protocol.py \
    --manifest results/spade-development-hill-000-050.jsonl.gz.manifest.json \
    --manifest results/spade-development-levy-000-050.jsonl.gz.manifest.json \
    --manifest results/spade-development-hartmann6-000-050.jsonl.gz.manifest.json \
    --manifest results/spade-development-ackley-000-050.jsonl.gz.manifest.json \
    --manifest results/spade-development-rosenbrock-000-050.jsonl.gz.manifest.json \
    > /tmp/spade-lofo-select.log 2>&1
  local ec=$?
  echo "LOFO_EXIT:$ec" >> /tmp/spade-lofo-select.log
  echo "LOFO done exit=$ec $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
  return $ec
}

while true; do
  date -u +%Y-%m-%dT%H:%M:%SZ > "$HB"
  backup_resumes

  if all_complete; then
    echo "ALL COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
    echo "ALL_COMPLETE" > "$HB"
    run_lofo || true
    rm -f "$LOCK"
    exit 0
  fi

  for fam in $FAMILIES; do
    is_complete "$fam" && continue
    worker_running "$fam" && continue
    n=$(count_running)
    if (( n >= MAX_CONCURRENT )); then
      echo "slot full; defer $fam (running=$n)" >> "$LOG"
      break
    fi
    start_family "$fam" || true
    sleep 2
  done

  {
    printf '%s ' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    for fam in $FAMILIES; do
      if is_complete "$fam"; then
        printf '%s=DONE ' "$fam"
      else
        printf '%s=%s%s ' "$fam" "$(row_count "$fam")" "$(worker_running "$fam" && echo '*' || echo '')"
      fi
    done
    echo
  } >> "$LOG"

  sleep "$POLL_SEC"
done
