"""KU adjudication. Implements `docs/SPADE-PREVALENCE-MATCHED-SPEC.md` §4 and §5 exactly.

Written BEFORE KU's data exists, so no gate can be tuned after seeing an outcome.

THE QUESTION
------------
KR-1 and KS-1 both failed a transfer test that was **confounded**: calibration sat on the
`tau_frac` grid at median target prevalence 0.9870 and the test sat on the tau-quantile grid at
0.3000 (§1). A cap fitted on targets covering 99% of the box was applied to targets covering
30%. KU puts `levy`, `rosenbrock`, `ackley` and `hartmann6` on **one** prevalence convention
(§5a excludes `hill` for the ensemble-evaluator reason) and asks whether leave-one-family-out
transfer clears 0.90 once that confound is removed.

THE CALIBRATION RULE IS §5 VERBATIM AND IS NOT A FREE PARAMETER
---------------------------------------------------------------
20 quantile strata of certified volume; the cap is the largest stratum edge at which the
one-sided 95% Clopper-Pearson UPPER bound on stratum-local failure stays <= 0.10, scanning
upward and stopping at the first stratum that fails.

**Out-of-range means ABSTAIN, never inherit the nearest stratum's verdict.** That was this
session's analyser erratum in KS: `+/-inf` outer edges let a test campaign outside the
calibration range take the extreme bin's admissibility, which is exactly the "never assumed
safe" failure §5 exists to prevent. `apply_1d` keeps the edges finite.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KU = ROOT / "results" / "ku-prevalence-matched.json"
TQ = ROOT / "results" / "tau-quantile-followup.json"
OUT = ROOT / "results" / "ku-analysis.json"

GAMMA = "0.95"
ALPHA = 0.10          # registered map-level failure budget
TARGET = 0.90         # registered containment claim
MIN_CELL = 25
ANSWER_FLOOR = 0.30   # KU-3
KU_FAMS = ("levy", "rosenbrock")          # from KU's own run
TQ_FAMS = ("ackley", "hartmann6")         # already committed, same grid


def cp_upper(k: int, n: int, d: float = 0.05) -> float:
    return 1.0 if n == 0 or k == n else float(beta.ppf(1 - d, k + 1, n - k))


def cp_lower(k: int, n: int, d: float = 0.05) -> float:
    return 0.0 if k == 0 else float(beta.ppf(d, k, n - k + 1))


def fit_1d(x: np.ndarray, c: np.ndarray) -> tuple[float, float]:
    """§5: largest stratum edge whose LOCAL failure upper bound stays <= ALPHA.
    Returns `(cap, lo)` -- both edges, because admissibility is bounded on BOTH sides."""
    edges = np.quantile(x, np.linspace(0, 1, 21))
    cap = 0.0
    for i in range(20):
        lo_e, hi_e = edges[i], edges[i + 1]
        m = (x >= lo_e) & (x <= hi_e) if i == 19 else (x >= lo_e) & (x < hi_e)
        if m.sum() < MIN_CELL:
            continue
        if cp_upper(int((1 - c[m]).sum()), int(m.sum())) <= ALPHA:
            cap = float(hi_e)
        else:
            break
    return cap, float(edges[0])


def apply_1d(cap: float, lo: float, x: np.ndarray) -> np.ndarray:
    """Inside the calibrated range AND under the cap. Outside it: abstain."""
    return (x >= lo) & (x <= cap)


def load() -> list[dict]:
    """All four families on the tau-quantile grid, non-empty certificates only."""
    out = []
    for path, fams in ((KU, KU_FAMS), (TQ, TQ_FAMS)):
        if not path.exists():
            raise SystemExit(f"missing {path} -- KU has not finished")
        for r in json.loads(path.read_text())["rows"]:
            fam = r.get("family") or r.get("instance")
            if fam not in fams or r.get(f"ce_empty_{GAMMA}"):
                continue
            out.append({"family": fam, "seed": int(r["seed"]), "arm": r["arm"],
                        "vol": float(r[f"ce_vol_{GAMMA}"]),
                        "contained": float(r[f"ce_empirical_{GAMMA}"])})
    return out


def main() -> None:
    rows = load()
    fams = sorted({r["family"] for r in rows})
    print(f"KU adjudication · gamma={GAMMA} · {len(rows)} non-empty certificates · "
          f"families={fams}\n")
    print("Leave-one-family-out: calibrate on the others, apply UNCHANGED to the held-out one.")
    print(f"{'held out':<13}{'cap':>10}{'uncal':>8}{'CALIB':>8}{'95% LB':>9}"
          f"{'answer':>8}{'n':>7}  verdict")

    per_family, pooled_k, pooled_n, pooled_ret, pooled_tot = {}, 0, 0, 0, 0
    for held in fams:
        cal = [r for r in rows if r["family"] != held]
        tst = [r for r in rows if r["family"] == held]
        xc = np.array([r["vol"] for r in cal]); cc = np.array([r["contained"] for r in cal])
        xt = np.array([r["vol"] for r in tst]); ct = np.array([r["contained"] for r in tst])
        cap, lo = fit_1d(xc, cc)
        m = apply_1d(cap, lo, xt)
        k, n = int(ct[m].sum()), int(m.sum())
        lb = cp_lower(k, n)
        ar = n / len(xt) if len(xt) else 0.0
        v = "PASS" if lb >= TARGET else "FAIL"
        print(f"{held:<13}{cap:>10.5g}{ct.mean():>8.4f}"
              f"{(ct[m].mean() if n else float('nan')):>8.4f}{lb:>9.4f}{ar:>8.3f}{n:>7}  {v}")
        per_family[held] = {"cap": cap, "uncalibrated": float(ct.mean()),
                            "calibrated": float(ct[m].mean()) if n else float("nan"),
                            "lower_bound_95": lb, "answer_rate": ar,
                            "n_retained": n, "verdict": v}
        pooled_k += k; pooled_n += n; pooled_ret += n; pooled_tot += len(xt)

    lb_pool = cp_lower(pooled_k, pooled_n)
    ku1 = "PASS" if lb_pool >= TARGET else "FAIL"
    n_pass = sum(1 for v in per_family.values() if v["verdict"] == "PASS")
    ku2 = "PASS" if n_pass >= 3 else "FAIL"
    ar_pool = pooled_ret / pooled_tot if pooled_tot else 0.0
    ku3 = "PASS" if ar_pool >= ANSWER_FLOOR else "FAIL"

    print(f"\nKU-1 (PRIMARY) pooled across held-out families: {pooled_k}/{pooled_n} = "
          f"{pooled_k/max(pooled_n,1):.4f}  95% LB {lb_pool:.4f}  (bar >= {TARGET}) -> {ku1}")
    print(f"   comparators, fixed: k_eff LB 0.8175 FAIL · kappa_tail LB 0.8074 FAIL")
    print(f"KU-2 per-family: {n_pass}/{len(fams)} clear LB >= {TARGET}  (bar 3 of 4) -> {ku2}")
    print(f"KU-3 pooled answer rate {ar_pool:.3f}  (bar >= {ANSWER_FLOOR}) -> {ku3}")

    if ku1 == "FAIL":
        print("\nKU-4 FIRES · the prevalence confound is NOT the explanation. The conservative "
              "excursion\n  certificate cannot be made family-general at 48 wells by any means "
              "this project has\n  tested -- region geometry (KR), surrogate fit (KS), or "
              "matching the scoring\n  convention (KU). Its validity scope must be DECLARED IN "
              "ADVANCE. With the 0/50 scope\n  detector that is four independent "
              "confirmations, and it is the paper's finding.")
    elif ku3 == "FAIL":
        print("\nNOTE: KU-1 passes but KU-3 does not -- calibrated, but rarely willing to "
              "answer.\n  Reported as such, not as a success (spec §4, KU-3).")

    OUT.write_text(json.dumps(
        {"spec": "docs/SPADE-PREVALENCE-MATCHED-SPEC.md", "gamma": GAMMA, "families": fams,
         "per_family": per_family,
         "KU_1": {"pooled_contained": pooled_k, "pooled_n": pooled_n,
                  "lower_bound_95": lb_pool, "verdict": ku1},
         "KU_2": {"n_pass": n_pass, "n_families": len(fams), "verdict": ku2},
         "KU_3": {"answer_rate": ar_pool, "verdict": ku3},
         "KU_4_fires": ku1 == "FAIL"}, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
