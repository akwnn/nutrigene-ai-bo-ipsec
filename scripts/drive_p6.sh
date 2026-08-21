#!/bin/zsh
# P6 cross-family driver. Registered order, registered fallback (cells 1+2, ~14 h).
#
#   family order : hartmann6 -> levy -> rosenbrock -> ackley   (OPEN-QUESTIONS.md P6)
#   cell order   : (6, 0.25) -> (6, 0.10)                      (cells 1+2 = the pair
#                  that gives the cross-family headline PLUS its sigma sensitivity)
#
# Halts the whole programme on any non-zero exit -- that is the registered kill and it is
# not repaired by rerunning. Every family resumes from its own checkpoint, so a halt
# costs only the campaign that failed.
set -u
cd "${0:A:h}/.." || exit 1
LOG=results/p6-drive.log
for cell in "6 0.25" "6 0.10"; do
  set -- ${=cell}; DIM=$1; SIG=$2
  for fam in hartmann6 levy rosenbrock ackley; do
    echo "=== $fam d=$DIM sigma=$SIG  start $(date +%H:%M:%S)" >> $LOG
    env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
      .venv/bin/python -u scripts/run_p6_families.py \
        --family $fam --dim $DIM --sigma $SIG \
        >> results/p6-$fam-d$DIM-s$SIG.log 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "HALT at $fam d=$DIM sigma=$SIG (exit $rc) -- registered kill or crash; see results/p6-$fam-d$DIM-s$SIG.log" >> $LOG
      exit $rc
    fi
    echo "=== $fam d=$DIM sigma=$SIG  done  $(date +%H:%M:%S)" >> $LOG
  done
done
echo "=== cells 1+2 complete $(date +%H:%M:%S); run --merge next" >> $LOG
