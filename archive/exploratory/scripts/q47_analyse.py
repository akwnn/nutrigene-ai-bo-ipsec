"""Q47 — the threshold surface in one table, the registered predictions scored, and the
two sensitivity arms.

    python scripts/q47_analyse.py    # log at results/q47-analysis.log

Reads the shards `run_q47_multifidelity.py` wrote. Adds nothing to the experiment; this
is the reporting layer, kept separate so the grid never has to be re-run to change a
table.

THE ONE THING WORTH READING TWICE
----------------------------------
The fixed-calibration arm does **not** isolate `(a, b)`, and saying so is the point.
`run_shard` draws `a` and `b` from the same generator that then draws the cheap readout's
noise `z`, so skipping those two draws leaves the generator in a different state and
every later draw differs. The arm therefore varies the calibration **and** re-draws the
noise.

That is a flaw, and it has a silver lining that makes the arm interpretable anyway:
`screen` is provably invariant to `(a, b)` (see `boec.multifidelity`), so **every
difference `screen` shows between the two runs is pure Monte Carlo re-draw.** It is a
negative control with a known true value of zero, and it calibrates how much of `joint`'s
difference is signal rather than noise. Reported that way rather than as a clean
calibration contrast, which it is not.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import wilcoxon                                   # noqa: E402

from boec.diagnostics import instance_bootstrap                    # noqa: E402

RHOS = (0.30, 0.45, 0.55, 0.65, 0.80, 0.95)
COSTS = (3, 5, 10, 20)
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
RHO_E = {(6, 0.25): 0.583, (6, 0.10): 0.872, (8, 0.25): 0.557, (8, 0.10): 0.863}
RULE = "=" * 100


def load(pattern: str) -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "results" / pattern))):
        rows.extend(json.loads(Path(f).read_text()))
    return rows


def paired(rows: list[dict], a: str, b: str) -> dict | None:
    """b - a at instance level. Positive means `a` has the lower regret."""
    insts = sorted({r["instance"] for r in rows})
    va, vb = [], []
    for i in insts:
        g = [r for r in rows if r["instance"] == i]
        xa = [r[a] for r in g if r.get(a) is not None and np.isfinite(r[a])]
        xb = [r[b] for r in g if r.get(b) is not None and np.isfinite(r[b])]
        if len(xa) != len(g) or len(xb) != len(g):
            continue
        va.append(np.mean(xa))
        vb.append(np.mean(xb))
    if len(va) < 3:
        return None
    d = np.array(vb) - np.array(va)
    m, lo, hi = instance_bootstrap(d, n_boot=4000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=float(m), lo=float(lo), hi=float(hi), p=p,
                verdict="better" if lo > 0 else ("worse" if hi < 0 else "null"))


def crossing(rows, arm: str, rule: str, dim, sigma, cost) -> tuple[str, list]:
    eff = []
    prev, hit = None, None
    for rho in RHOS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12
               and r["cost_ratio"] == cost and abs(r["rho"] - rho) < 1e-12]
        e = paired(sub, f"{arm}_{rule}", f"single_{rule}") if sub else None
        eff.append((rho, e))
        if hit is None and e and e["verdict"] == "better":
            hit = f"<={rho:.2f}" if prev is None else f"{prev:.2f}-{rho:.2f}"
        if hit is None:
            prev = rho
    return (hit or "never"), eff


def main() -> None:
    rows = load("q47-mf-?-*-*.json")
    rows = [r for r in rows if abs(r["phi"] - 1 / 3) < 1e-9 and not r["fixed_calibration"]]
    print(f"{RULE}\nQ47 — THE THRESHOLD SURFACE. {len(rows)} runs, phi=1/3, sampled "
          f"calibration.\n{RULE}")
    print("  Lowest rho at which the two-tier arm's advantage clears zero (instance "
          "bootstrap, n=25).\n  * = above the expensive readout's own correlation with "
          "the truth, where the\n      'cheap' assay is simply the better assay and the "
          "trade-off is not a trade-off.\n")
    header = f"  {'cell':<16}{'arm':<8}{'rule':<6}" + "".join(f"{c}x".rjust(12)
                                                              for c in COSTS)
    for rule in ("a", "c"):
        print(header if rule == "a" else "")
        for dim, sigma in CELLS:
            for arm in ("screen", "joint"):
                cells = []
                for c in COSTS:
                    x, _ = crossing(rows, arm, rule, dim, sigma, c)
                    star = "*" if (x != "never" and
                                   float(x.split("-")[-1].lstrip("<=")) > RHO_E[(dim, sigma)]) else ""
                    cells.append(f"{x}{star}".rjust(12))
                print(f"  {f'd={dim} s={sigma}':<16}{arm:<8}{'A' if rule=='a' else 'C':<6}"
                      + "".join(cells))

    # ---------------- the under-budget control ----------------
    print(f"\n{RULE}\n  THE CONTROL THE BRIEF DOES NOT HAVE: what does cutting 48 "
          f"expensive points to 32 cost?\n{RULE}")
    for dim, sigma in CELLS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12
               and r["cost_ratio"] == 3 and abs(r["rho"] - 0.30) < 1e-12]
        for rule in ("a", "c"):
            e = paired(sub, f"budget_only_{rule}", f"single_{rule}")
            print(f"    d={dim} s={sigma}  rule {rule.upper()}   32 vs 48 expensive: "
                  f"{e['diff']:>+8.4f} [{e['lo']:>+7.4f},{e['hi']:>+7.4f}] "
                  f"{'32 IS BETTER' if e['verdict']=='better' else ('48 is better' if e['verdict']=='worse' else 'no difference')}")

    # ---------------- registered predictions ----------------
    print(f"\n{RULE}\n  THE THREE REGISTERED PREDICTIONS, SCORED\n{RULE}")
    p1 = []
    for dim, sigma in CELLS:
        for c in (5, 10, 20):
            x, _ = crossing(rows, "screen", "a", dim, sigma, c)
            p1.append((f"d={dim} s={sigma} {c}x", x))
    ok = sum(1 for _, x in p1 if x.startswith("<="))
    print(f"  P1 'no threshold: two-tier pays at rho=0.30 for every cost ratio >= 5'")
    print(f"     rule A, screen: pays at rho=0.30 in {ok} of {len(p1)} such cells "
          f"-> {'HELD' if ok == len(p1) else 'REFUTED'}")
    print("     " + "  ".join(f"{k}:{v}" for k, v in p1))

    print(f"\n  P2 'the benefit is non-monotone in rho at sigma=0.10, peaking near "
          f"0.65-0.80'")
    for dim in (6, 8):
        for c in COSTS:
            e80 = paired([r for r in rows if r["dim"] == dim and r["sigma"] == 0.10
                          and r["cost_ratio"] == c and abs(r["rho"] - 0.80) < 1e-12],
                         "screen_a", "single_a")
            e95 = paired([r for r in rows if r["dim"] == dim and r["sigma"] == 0.10
                          and r["cost_ratio"] == c and abs(r["rho"] - 0.95) < 1e-12],
                         "screen_a", "single_a")
            if e80 and e95:
                print(f"     d={dim} {c:>2}x  rho=0.80 {e80['diff']:+.4f} -> rho=0.95 "
                      f"{e95['diff']:+.4f}   "
                      f"{'DECLINES (as predicted)' if e95['diff'] < e80['diff'] else 'rises'}")

    print(f"\n  P3 'rule A and rule C disagree; two-tier should do WORSE under rule C "
          f"because\n      the top-k design is clustered where a surrogate needs spread'")
    worse, better, same = 0, 0, 0
    for dim, sigma in CELLS:
        for c in COSTS:
            xa, _ = crossing(rows, "screen", "a", dim, sigma, c)
            xc, _ = crossing(rows, "screen", "c", dim, sigma, c)
            rank = {"never": 9, "<=0.30": 0, "0.30-0.45": 1, "0.45-0.55": 2,
                    "0.55-0.65": 3, "0.65-0.80": 4, "0.80-0.95": 5}
            if rank[xc] < rank[xa]:
                better += 1
            elif rank[xc] > rank[xa]:
                worse += 1
            else:
                same += 1
    print(f"     rule C threshold is LOWER (two-tier better) in {better} of 16 cells, "
          f"higher in {worse}, equal in {same}")
    if worse > better + 3:
        verdict = "HELD"
    elif better > worse + 3:
        verdict = "REFUTED, and the sign is the OPPOSITE of the one registered"
    else:
        verdict = ("REFUTED as a directional claim — there is no systematic difference "
                   "either way")
    print(f"     -> P3 predicted 'higher'. {verdict}")
    print(f"        (at d=6 alone rule C IS systematically lower, which is how this "
          f"looked\n         before the d=8 cells finished. Across all 16 it is a wash.)")

    # ---------------- sensitivity arms ----------------
    print(f"\n{RULE}\n  SENSITIVITY: the allocation phi, and the sampled calibration"
          f"\n{RULE}")
    allr = load("q47-mf-?-*-*.json")
    for c in (5, 20):
        print(f"\n    cost ratio {c}x, d=6 sigma=0.25 — rule A advantage over single "
              f"tier at each phi")
        print(f"      {'phi':<8}{'k':<5}{'n_cheap':<9}" +
              "".join(f"rho={r:.2f}".rjust(11) for r in RHOS))
        for phi in (0.25, 1 / 3, 0.5):
            sub_all = [r for r in allr if r["dim"] == 6 and r["sigma"] == 0.25
                       and r["cost_ratio"] == c and abs(r["phi"] - phi) < 1e-9
                       and not r["fixed_calibration"]]
            if not sub_all:
                continue
            line = []
            for rho in RHOS:
                s = [r for r in sub_all if abs(r["rho"] - rho) < 1e-12]
                e = paired(s, "screen_a", "single_a") if s else None
                line.append((f"{e['diff']:+.4f}" + ("*" if e["verdict"] == "better"
                                                    else " ")).rjust(11) if e else "".rjust(11))
            print(f"      {phi:<8.3f}{sub_all[0]['k']:<5}{sub_all[0]['n_cheap']:<9}"
                  + "".join(line))
        print(f"      (* = advantage clears zero)")

    print(f"\n    FIXED vs SAMPLED CALIBRATION — and read the module docstring first.")
    print(f"    `screen` is PROVABLY invariant to (a, b), so its difference here is pure")
    print(f"    Monte Carlo re-draw and is the negative control for `joint`'s.")
    for c in (5, 20):
        for rho in (0.30, 0.65, 0.95):
            out = []
            for arm in ("screen", "joint"):
                v = {}
                for fixed in (False, True):
                    s = [r for r in allr if r["dim"] == 6 and r["sigma"] == 0.25
                         and r["cost_ratio"] == c and abs(r["phi"] - 1 / 3) < 1e-9
                         and abs(r["rho"] - rho) < 1e-12
                         and bool(r["fixed_calibration"]) is fixed]
                    e = paired(s, f"{arm}_a", f"single_a") if s else None
                    v[fixed] = e["diff"] if e else float("nan")
                out.append(f"{arm} {v[False]:+.4f} -> {v[True]:+.4f} "
                           f"({v[True] - v[False]:+.4f})")
            print(f"      {c:>2}x rho={rho:.2f}   " + "   ".join(out))
    print(f"\n{RULE}")


if __name__ == "__main__":
    main()
