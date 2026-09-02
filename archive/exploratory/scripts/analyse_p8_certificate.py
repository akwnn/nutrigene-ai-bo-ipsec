"""P8 · SPADE's certificate off hill, ADJUDICATED.

    .venv/bin/python scripts/analyse_p8_certificate.py --file results/p8-certificate-families.json

§35's lesson, one level up: a registered run whose columns nothing adjudicates is a
paragraph. P8 produces 24,000 rows of certificate columns across five families. This turns
them into a verdict, and refuses three specific ways that verdict could be a lie.

THE THREE TRAPS
---------------
**1. `ce_contain` is CIRCULAR.** ``conservative_estimate`` selects on it, so it cannot fall
below alpha — F3 (§29) is the whole story of what happens when a circular statistic is read
as evidence. It is reported here for completeness and **refused** as a containment source.

**2. `ce_empirical` is `nan` for an EMPTY set.** An empty certificate is vacuously
contained. If empties counted as successes, a cell where 47 of 50 campaigns certified
*nothing* and the remaining 3 happened to contain the optimum would report **containment
1.000** — a perfect score for a method that mostly declined to answer. Empties therefore
leave the numerator **and** the denominator, `n_scored` travels with every rate, and the
empty rate is printed beside it.

**3. Exact binomial tails, never a normal approximation** (Erratum 21). The continuity
correction is what turned §14's "one failure survives Holm" into an artefact.

WHAT THIS IS NOT
----------------
**Not a kill.** §29 withdrew *"SPADE's certificate fails below nominal at high assurance"* —
that reading was an artefact of 512 draws. P8 runs at 4,096 and **records** where containment
sits, with its exact tail and Holm across cells. A cell below nominal is a measurement, not a
verdict. ``VERDICT_IS_DESCRIPTIVE`` says so in the code rather than only in prose.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[1]

#: The VALIDATED containment statistic. `ce_contain` is the circular one and is refused.
CONTAINMENT_COLUMN = "ce_empirical"
CIRCULAR_COLUMN = "ce_contain"

ALPHAS = (0.50, 0.80, 0.95)

#: P8 records; it does not kill. §29 withdrew the below-nominal kill.
VERDICT_IS_DESCRIPTIVE = True

#: The registered prediction, stated before any number existed (OPEN-QUESTIONS, P8 block).
REGISTERED_PREDICTION = ("containment at gamma=0.95 will be LOWER off hill than on it, "
                         "because §20 found the certifiability ceiling is ordered by "
                         "max tau_q and the families differ sharply on it")


class CircularStatisticRefused(RuntimeError):
    """`ce_contain` cannot fall below alpha. A containment claim built on it is a tautology."""


def exact_tail(n_contained: int, n: int, alpha: float):
    """`P(X <= n_contained | n, alpha)`. Exact. `None` when there is no denominator."""
    if n <= 0:
        return None
    return float(binom.cdf(n_contained, n, alpha))


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni, monotone in the sorted order. `None` values pass through."""
    live = {k: v for k, v in pvals.items() if v is not None}
    out = {k: None for k in pvals if k not in live}
    order = sorted(live, key=lambda k: live[k])
    m, running = len(order), 0.0
    for i, k in enumerate(order):
        adj = min(1.0, live[k] * (m - i))
        running = max(running, adj)          # enforce monotonicity
        out[k] = running
    return out


def containment_rate(rows: list, alpha: float, column: str = CONTAINMENT_COLUMN) -> dict:
    """Empirical containment for one cell. **Empties leave both numerator and denominator.**"""
    if column.startswith(CIRCULAR_COLUMN):
        raise CircularStatisticRefused(
            f"{column!r} is the circular statistic: conservative_estimate selects on it, so "
            f"it cannot fall below alpha and a containment claim built on it is a "
            f"tautology (F3, §29). Use {CONTAINMENT_COLUMN!r}.")
    key, empty_key = f"{column}_{alpha}", f"ce_empty_{alpha}"
    n_total = len(rows)
    vals, n_empty = [], 0
    for r in rows:
        v = r.get(key)
        if r.get(empty_key) or v is None or (isinstance(v, float) and math.isnan(v)):
            n_empty += 1
            continue
        vals.append(float(v))
    n_scored = len(vals)
    n_contained = sum(1 for v in vals if v >= alpha)
    return {
        "alpha": alpha, "n_total": n_total, "n_scored": n_scored, "n_empty": n_empty,
        "empty_rate": (n_empty / n_total) if n_total else None,
        "n_contained": n_contained,
        "rate": (n_contained / n_scored) if n_scored else None,
        "mean_empirical": (st.mean(vals) if vals else None),
        "exact_tail": exact_tail(n_contained, n_scored, alpha),
        "scored_fraction": (n_scored / n_total) if n_total else None,
    }


def analyse(rows: list, gamma: float, tau_frac: float, arm: str) -> dict:
    """Every family at one `(gamma, tau_frac, arm)` cell."""
    sub = [r for r in rows
           if abs(float(r["gamma"]) - gamma) < 1e-9
           and abs(float(r["tau_frac"]) - tau_frac) < 1e-9
           and r["arm"] == arm]
    by_family = defaultdict(list)
    for r in sub:
        by_family[r["family"]].append(r)

    per_family, tails = {}, {}
    for fam, fr in sorted(by_family.items()):
        cell = {a: containment_rate(fr, a) for a in ALPHAS}
        astar = [r["alpha_star"] for r in fr
                 if r.get("alpha_star") is not None
                 and not (isinstance(r["alpha_star"], float) and math.isnan(r["alpha_star"]))]
        per_family[fam] = {
            "containment": cell,
            "alpha_star_mean": (st.mean(astar) if astar else None),
            "n_campaigns": len(fr),
        }
        tails[fam] = cell[0.95]["exact_tail"]
    return {"gamma": gamma, "tau_frac": tau_frac, "arm": arm,
            "per_family": per_family, "holm_0.95": holm(tails)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "results" / "p8-certificate-families.json"))
    ap.add_argument("--arm", default="versionb")
    ap.add_argument("--gamma", type=float, default=0.95)
    ap.add_argument("--tau-frac", type=float, default=0.60)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    src = Path(args.file)
    payload = json.loads(src.read_text())
    rows = payload["rows"]
    status = payload.get("status", "?")
    print(f"P8 certificate · {src.name} · status={status} · {len(rows)} rows")
    print(f"arm={args.arm} gamma={args.gamma} tau_frac={args.tau_frac} "
          f"n_draws={payload.get('config', {}).get('n_draws')}")
    print(f"containment from {CONTAINMENT_COLUMN}_*; {CIRCULAR_COLUMN}_* is CIRCULAR and "
          f"is not used\n")

    v = analyse(rows, args.gamma, args.tau_frac, args.arm)
    print(f"  {'family':<12}{'n':>4}{'scored':>8}{'empty':>8}"
          f"{'contain@.95':>13}{'mean emp':>10}{'exact tail':>12}{'holm':>10}"
          f"{'alpha*':>9}")
    for fam, f in v["per_family"].items():
        c = f["containment"][0.95]
        rate = "  n/a" if c["rate"] is None else f"{c['rate']:.3f}"
        me = "   n/a" if c["mean_empirical"] is None else f"{c['mean_empirical']:.4f}"
        et = "     n/a" if c["exact_tail"] is None else f"{c['exact_tail']:.3e}"
        hm = v["holm_0.95"].get(fam)
        hms = "     n/a" if hm is None else f"{hm:.3e}"
        ast = "   n/a" if f["alpha_star_mean"] is None else f"{f['alpha_star_mean']:.4f}"
        print(f"  {fam:<12}{c['n_total']:>4}{c['n_scored']:>8}{c['n_empty']:>8}"
              f"{rate:>13}{me:>10}{et:>12}{hms:>10}{ast:>9}")

    print(f"\n  registered prediction: {REGISTERED_PREDICTION}")
    hill = v["per_family"].get("hill", {}).get("containment", {}).get(0.95, {})
    others = {f: d["containment"][0.95]["rate"] for f, d in v["per_family"].items()
              if f != "hill" and d["containment"][0.95]["rate"] is not None}
    if hill.get("rate") is not None and others:
        lower = [f for f, r in others.items() if r < hill["rate"]]
        print(f"  hill = {hill['rate']:.3f}; lower off hill on "
              f"{len(lower)}/{len(others)} families {sorted(lower)}")
    print("\n  NOT A KILL: §29 withdrew the below-nominal kill. This records, with its "
          "exact tail.")

    if args.out:
        Path(args.out).write_text(json.dumps(
            {"source": src.name, "status": status, "arm": args.arm,
             "containment_column": CONTAINMENT_COLUMN,
             "circular_column_refused": CIRCULAR_COLUMN,
             "verdict_is_descriptive": VERDICT_IS_DESCRIPTIVE,
             "registered_prediction": REGISTERED_PREDICTION,
             "cell": v}, indent=1))
        print(f"\nwrote {Path(args.out).name}")


if __name__ == "__main__":
    main()
