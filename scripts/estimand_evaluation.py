"""Estimand evaluation — the two questions the STORED data can actually answer.

    python scripts/estimand_evaluation.py

NO NEW CAMPAIGNS. Everything here reads committed artefacts. That constraint is
also the headline finding: `results/e2-grid.json` stores eight summary fields per
campaign and **no visited points**, so most alternative estimands cannot be
computed at all without re-running. Q29 said this in one line and it governs the
whole exercise — *"`results/e2-grid.json` stores summary rows only, no visited
points."*

§1 — WHERE RULE A STOPS MEASURING OPTIMISATION
-----------------------------------------------
Rule A scores the best OBSERVED point. Under noise the best observation is a
minimum-of-n order statistic, so it improves with budget for two reasons that
point in opposite directions: the arm genuinely finds better places, and the
noise draw at the luckiest visited point gets more extreme. Past some n the
second dominates and more budget makes the *score* worse while the *search* is
still improving.

`q52-floor.json` holds rule A and rule C per instance at n = 24/48/96/192/384 on
a planted space-filling design, all four cells. That is exactly the curve needed:
the budget minimising mean rule-A regret is the crossover, and the registered
budget of 48 sits somewhere relative to it.

**Scope, stated rather than silent:** this is a static space-filling family, not
qLogEI. Q52 §1.2 established that concentration is protective under rule A, so an
adaptive arm's crossover is LATER than this one. The number below is therefore a
lower bound on the crossover for the adaptive arms and an exact one for the
static arms — which are three of the seven in E2.

§2 — PROBABILITY OF CORRECT SELECTION
--------------------------------------
Of the seven alternative estimands surveyed, PCS is the only one computable from
the stored grid, because it is a function of per-campaign regret alone: did this
run land within epsilon of the optimum, yes or no. It is a genuinely different
question from mean regret — it is robust to the outlying landscape that a mean
chases — and the registered target list supplies the epsilons.

If PCS agrees with rule A the estimand finding is narrower than "two rules".
If it disagrees, there is a third defensible convention and the binary framing
weakens. Either way it is reported, per Part 6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.discrimination import paired_difference_ci  # noqa: E402

RULE = "=" * 96
RESULTS = ROOT / "results"
CELLS = [(6, 0.25), (6, 0.1), (8, 0.25), (8, 0.1)]


def cell_name(dim: int, sigma: float) -> str:
    star = "  <-- registered primary" if (dim, sigma) == (6, 0.25) else ""
    return f"d={dim} sigma={sigma}{star}"


def section_1() -> dict:
    floor = json.loads((RESULTS / "q52-floor.json").read_text())
    ns = floor["ns"]
    out = {}

    print(f"{RULE}\n  SECTION 1 — the budget at which rule A stops rewarding search\n{RULE}")
    print(f"  source: results/q52-floor.json | planted space-filling design, 25 instances")
    print(f"  budgets: {ns}\n")

    for dim, sigma in CELLS:
        rows = {r["n"]: r for r in floor["rows"] if r["dim"] == dim and r["sigma"] == sigma}
        if not all(n in rows for n in ns):
            print(f"  {cell_name(dim, sigma)}: incomplete, skipped")
            continue

        a_means = [float(np.mean(rows[n]["rule_a"])) for n in ns]
        c_means = [float(np.mean(rows[n]["rule_c"])) for n in ns]
        best_n = ns[int(np.argmin(a_means))]

        print(f"  {cell_name(dim, sigma)}")
        print(f"    {'n':<8}" + "".join(f"{n:>10}" for n in ns))
        print(f"    {'rule A':<8}" + "".join(f"{v:>10.4f}" for v in a_means))
        print(f"    {'rule C':<8}" + "".join(f"{v:>10.4f}" for v in c_means))

        # paired, instance level: does rule A get WORSE from its own minimum to 384?
        lo_i = ns.index(best_n)
        a_lo = rows[ns[lo_i]]["rule_a"]
        a_hi = rows[ns[-1]]["rule_a"]
        d, lo, hi, _ = paired_difference_ci(a_hi, a_lo, seed=0)
        worse = lo > 0.0
        print(f"    rule A minimises at n={best_n}; n={ns[-1]} minus n={best_n} = "
              f"{d:+.4f} [{lo:+.4f}, {hi:+.4f}] "
              f"{'WORSE with more budget, CI clear of zero' if worse else 'not clear of zero'}")

        c_d, c_lo, c_hi, _ = paired_difference_ci(rows[ns[-1]]["rule_c"], rows[ns[0]]["rule_c"], seed=0)
        print(f"    rule C, n={ns[-1]} minus n={ns[0]}   = {c_d:+.4f} [{c_lo:+.4f}, {c_hi:+.4f}]"
              f"{'  (improves)' if c_hi < 0 else ''}")
        print(f"    registered budget 48 is {'BELOW' if 48 < best_n else 'AT OR ABOVE'} the crossover\n")

        out[f"d{dim}-s{sigma}"] = dict(ns=ns, rule_a=a_means, rule_c=c_means,
                                       crossover_n=best_n, budget_48_below=bool(48 < best_n),
                                       a_hi_minus_lo=[d, lo, hi])
    return out


def section_2() -> dict:
    grid = json.loads((RESULTS / "e2-grid.json").read_text())
    doe8 = json.loads((RESULTS / "e2-doe-d8.json").read_text())   # D17: it exists
    rows = grid + [r for r in doe8 if r["arm"] == "doe"]
    targets = json.loads((RESULTS / "q52-floor.json").read_text())["targets"]
    out = {}

    print(f"{RULE}\n  SECTION 2 — probability of correct selection, P(regret <= eps)\n{RULE}")
    print(f"  source: results/e2-grid.json + results/e2-doe-d8.json | 50 campaigns per arm-cell")
    print(f"  the ONLY alternative estimand computable from stored data: it needs regret alone\n")

    for dim, sigma in CELLS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
        arms = sorted({r["arm"] for r in sub})
        if not arms:
            continue
        print(f"  {cell_name(dim, sigma)}")
        print(f"    {'arm':<10}{'mean reg':>10}" + "".join(f"{t:>8}" for t in targets))
        table = {}
        for arm in arms:
            reg = [r["regret"] for r in sub if r["arm"] == arm]
            pcs = [float(np.mean([x <= t for x in reg])) for t in targets]
            table[arm] = dict(mean_regret=float(np.mean(reg)), pcs=pcs, n=len(reg))
            print(f"    {arm:<10}{np.mean(reg):>10.4f}" + "".join(f"{p:>8.2f}" for p in pcs))

        # the headline contrast, under PCS instead of mean regret
        if "doe" in table and "qlogei" in table:
            print(f"    --- qlogei minus doe (negative = DoE better) ---")
            print(f"    {'mean regret':<14}{table['qlogei']['mean_regret'] - table['doe']['mean_regret']:+.4f}")
            flips = []
            for t, pq, pd in zip(targets, table["qlogei"]["pcs"], table["doe"]["pcs"]):
                # PCS is a hit RATE: higher is better, so BO ahead when pq > pd
                flips.append((t, pq - pd))
            print(f"    {'PCS diff':<14}" + "".join(f"{v:>+8.2f}" for _, v in flips)
                  + "   (positive = BO selects correctly more often)")
        print()
        out[f"d{dim}-s{sigma}"] = table
    return out


def main() -> None:
    s1 = section_1()
    s2 = section_2()
    (RESULTS / "estimand-evaluation.json").write_text(
        json.dumps(dict(section_1_crossover=s1, section_2_pcs=s2), indent=1))
    print(f"  written to results/estimand-evaluation.json")


if __name__ == "__main__":
    main()
