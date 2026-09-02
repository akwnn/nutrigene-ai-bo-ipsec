"""Q16 / TASKS T1 — the ACTUAL coverage rate, not a ratio of two medians.

    python scripts/pf1_coverage.py           # the full 40-instance grid, ~1.5 min
    python scripts/pf1_coverage.py 4         # quick pass while developing

Results: results/pf1-coverage.log

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

Q16's replacement primary is:

> *the second-order model's prediction interval loses nominal coverage of the
> true response as rho increases, and we report the rho at which it crosses.*

The objection filed against it (Q16, B's answer) used
``median(over) / median(pi/2)`` and found that ratio non-monotone. **That is not
a coverage rate.** A ratio of two medians can be non-monotone while
``P(|over| <= pi/2)`` is perfectly monotone, so it raises a well-posedness risk
without establishing one. ``preflight_pf1`` already records ``over`` and ``pi``
for all 800 cells, so the real quantity is a reporting change rather than a new
experiment. This computes it.

    covered   <=>   |over| <= pi/2        (pi is the FULL interval width)
    coverage(kappa, rho) = mean(covered)

Aggregated with an **instance-level cluster bootstrap**: four kappa on one
landscape are four measurements of one landscape, not four independent
observations. Same nested-clustering fix as `0fc2610`.

------------------------------------------------------------------------------
WHAT IT FOUND, AND WHY IT MATTERS MORE THAN THE OBJECTION IT WAS CHECKING
------------------------------------------------------------------------------

**At the model's own constrained argmax, coverage is nowhere near nominal at any
setting** — 0.00 to 0.63 across all twenty (kappa, rho) cells, against a nominal
of 0.95. Including at rho = 1.2.

So the replacement primary has **zero** crossings to report, not two. The
objection is upheld, but not for the reason it gave: the crossing rho is
undefined because the interval never had nominal coverage to lose, not because
it loses it more than once.

**This does not contradict A's 96-98% at rho=1.2 — it measures a different
thing, and the primary never says which.** A's figure is coverage over the
design or the domain; this is coverage *at the recipe the model tells you to
run*, which is the worst case by construction and the one a practitioner
actually faces. Both are legitimate; they give opposite verdicts on the same
registered sentence. **That ambiguity is the defect to fix before the run** —
name the point set in the pre-registration.

Coverage is also non-monotone in rho at every kappa, dipping and then recovering
toward the unit cube. That is consistent with the saturation mechanism already
argued in Q16: once the box stops growing the argmax stops moving outward while
``sigma*sqrt(1 + h)`` keeps inflating on the sub-box design's ill-conditioning.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
import warnings
from pathlib import Path

import numpy as np
import torch

torch.set_num_threads(1)
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from preflight_pf1 import KAPPAS, RHOS, rho_label, run  # noqa: E402

NOMINAL = 0.95
N_BOOT = 2000
RULE = "=" * 78


def cluster_bootstrap(by_instance: dict[str, list[bool]], seed: int = 0):
    """Coverage and its 95% CI, resampling **instances** with replacement."""
    ids = sorted(by_instance)
    per = {i: np.asarray(by_instance[i], dtype=float) for i in ids}
    rng = np.random.default_rng(seed)
    n = len(ids)
    point = float(np.concatenate([per[i] for i in ids]).mean())
    draws = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = [ids[j] for j in rng.integers(0, n, n)]
        draws[b] = np.concatenate([per[i] for i in pick]).mean()
    return point, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main() -> None:
    n_instances = int(sys.argv[1]) if len(sys.argv) > 1 else None
    rows = run(n_instances)
    n_inst = len({r["instance"] for r in rows})
    print(f"PF1 COVERAGE · {len(rows)} cells · {n_inst} instances · d=6")
    print(f"covered <=> |over| <= pi/2, at the second-order model's own argmax\n")

    print(RULE, f"\nCOVERAGE OF THE TRUE RESPONSE (nominal {NOMINAL:.2f})\n", RULE, sep="")
    print("  kappa  " + "".join(f"{rho_label(r):>18}" for r in RHOS))

    table: dict[tuple[float, float], tuple[float, float, float]] = {}
    for k in KAPPAS:
        cells = []
        for r in RHOS:
            by_inst: dict[str, list[bool]] = {}
            for row in rows:
                if row["kappa"] == k and row["rho"] == r:
                    by_inst.setdefault(row["instance"], []).append(
                        abs(row["over"]) <= row["pi"] / 2.0
                    )
            pt, lo, hi = cluster_bootstrap(by_inst)
            table[(k, r)] = (pt, lo, hi)
            cells.append(f"{pt:.3f} [{lo:.2f},{hi:.2f}]".rjust(18))
        print(f"   {k:<5}" + "".join(cells))

    best = max(pt for pt, _, _ in table.values())
    print(f"\n  Highest coverage anywhere on the grid: {best:.3f}, against nominal {NOMINAL:.2f}.")

    print("\n" + RULE, "\nMONOTONE IN rho?\n", RULE, sep="")
    for k in KAPPAS:
        s = [table[(k, r)][0] for r in RHOS]
        rises = [f"{rho_label(RHOS[i])}->{rho_label(RHOS[i + 1])}"
                 for i in range(len(RHOS) - 1) if s[i + 1] > s[i] + 1e-12]
        print(f"   kappa={k}: {'monotone decreasing' if not rises else 'NOT monotone'}"
              + (f"   rises at {', '.join(rises)}" if rises else ""))

    print("\n" + RULE, "\nCROSSINGS OF NOMINAL — the registered quantity\n", RULE, sep="")
    n_cross: dict[float, int] = {}
    for k in KAPPAS:
        s = [table[(k, r)][0] for r in RHOS]
        above = [v >= NOMINAL for v in s]
        cross = [(rho_label(RHOS[i]), rho_label(RHOS[i + 1]))
                 for i in range(len(RHOS) - 1) if above[i] != above[i + 1]]
        n_cross[k] = len(cross)
        if not cross:
            why = ("never reaches nominal at any rho" if not any(above)
                   else "never falls below nominal")
            print(f"   kappa={k}: 0 crossings — {why}")
        else:
            print(f"   kappa={k}: {len(cross)} crossing(s) at "
                  + ", ".join(f"{a}->{b}" for a, b in cross))

    print("\n" + RULE, "\nVERDICT\n", RULE, sep="")
    if all(v == 0 for v in n_cross.values()):
        never = all(table[(k, r)][0] < NOMINAL for k in KAPPAS for r in RHOS)
        if never:
            print("  The registered primary has NO crossing to report, at any kappa.")
            print("  Coverage at the argmax starts below nominal at rho=1.2 and stays there,")
            print("  so the interval never had nominal coverage to lose. 'The rho at which")
            print("  it crosses' is undefined on this point set — a stronger failure than")
            print("  the multiple-crossings objection, and a different one.")
            print()
            print("  NOT a contradiction of A's 96-98% at rho=1.2: that measures coverage")
            print("  over the design/domain, this measures it at the recipe the model tells")
            print("  you to run. The primary does not say which, and they disagree on the")
            print("  verdict. Name the point set before the run.")
        else:
            print("  Coverage never falls below nominal — the registered claim fails, and")
            print("  that is a real finding.")
    elif max(n_cross.values()) > 1:
        print("  At least one kappa crosses nominal more than once, so the crossing rho is")
        print("  not well defined there. The objection is upheld on the real rate.")
    else:
        print("  Exactly one crossing at every kappa: the registered quantity is well")
        print("  defined and the objection does not survive on the real coverage rate.")


if __name__ == "__main__":
    main()
