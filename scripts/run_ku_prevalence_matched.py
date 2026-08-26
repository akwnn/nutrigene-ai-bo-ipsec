"""KU · score hill/levy/rosenbrock on the tau-QUANTILE grid.

Registered in `docs/SPADE-PREVALENCE-MATCHED-SPEC.md`, frozen at `9a4f0c1`-era commit
**before this file existed**.

WHY A WRAPPER AND NOT A FORK
----------------------------
`run_tau_quantile_followup.py` already implements exactly the scoring KU needs -- quantile
taus, `P_VALUES = (0.30, 0.10, 0.03, 0.01)`, `N_DRAWS = 4096`, the P8 regeneration gate. It
differs from KU in **families only**: its `FAMILIES` constant is `("ackley", "hartmann6")`.

`FAMILIES` is read from module scope inside `score_family`/`main`, not bound as a default
argument, so rebinding it before the call is sufficient and does not touch the committed file.
(That is the opposite of `score_campaign`'s `alphas=ALPHAS`, which IS a default argument and
therefore could not be patched -- see `run_kt_assurance_fast.py`'s header.)

Output goes to a **separate** file. `results/tau-quantile-followup.json` is a committed record
of a completed, adjudicated study and is not appended to.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KU_FAMILIES = ("levy", "rosenbrock")   # hill excluded: ensemble evaluator path, see spec §5a
#: Spec §5: 25, reduced from 50 BEFORE the run because the comparable path measures
#: ~85-113 s/campaign and 600 campaigns would project past the 8-hour ceiling.
KU_SEEDS = 25


def load_tq():
    path = Path(__file__).parent / "run_tau_quantile_followup.py"
    spec = importlib.util.spec_from_file_location("_ku_tq", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                       # type: ignore[union-attr]
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0,
                    help="firewalled timing pilot: N seeds of hill only, nothing written")
    ap.add_argument("--seeds", type=int, default=KU_SEEDS)
    ap.add_argument("--out", type=Path,
                    default=ROOT / "results" / "ku-prevalence-matched.json")
    args = ap.parse_args()

    import time

    from boec.norms import sobol_grid

    TQ = load_tq()
    TQ.FAMILIES = KU_FAMILIES                     # module-scope rebind; see header
    TQ.OUT = args.out

    grid = sobol_grid(TQ.DIM, TQ.P2.GRID_N, seed=TQ.P2.GRID_SEED)
    X_sub = sobol_grid(TQ.DIM, TQ.P2.SUBSET_N, seed=TQ.P2.GRID_SEED)

    if args.pilot:
        t0 = time.time()
        rows, tau_by_p = TQ.score_family("levy", grid, X_sub, range(args.pilot), {}, [])
        dt = time.time() - t0
        n = args.pilot * len(TQ.ARMS)
        total = len(KU_FAMILIES) * len(TQ.ARMS) * args.seeds
        print(f"PILOT · {n} campaigns · {dt:.1f}s · {dt/n:.1f}s each")
        print(f"levy tau_by_p: {tau_by_p}")
        print(f"projected KU full run ({len(KU_FAMILIES)} families x {len(TQ.ARMS)} arms x "
              f"{args.seeds} seeds = {total}): {dt/n*total/3600:.2f} h")
        if dt / n * total / 3600 > 8.0:
            print("\nEXCEEDS spec §5's 8-hour ceiling even at the reduced seed count. "
                  "Per §5 the next reduction is ARMS -> (versionb, plate1_only). "
                  "Reported, not silently extended.")
        print("TIMING ONLY -- no outcome inspected, nothing written")
        return

    sys.argv = ["run_tau_quantile_followup.py", "--seeds", str(args.seeds)]
    TQ.main()


if __name__ == "__main__":
    main()
