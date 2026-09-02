"""The BO community's own metrics, and Version C's alpha*-analogue. Committed data only.

    .venv/bin/python scripts/analyse_versionc_conventions.py

The coverage brief recorded **zero coverage** for the BO conventions -- mean rank and a
performance profile. FINDINGS §33 closed the RSM half (lack of fit, FDS, G/D-efficiency,
confirmation agreement). This closes the BO half.

**Both terminal rules are reported side by side, always.** A rule-P regret is not
comparable to a published rule-A number -- they are different estimands -- and §40.1
records what happens when that is forgotten. Every table here says which column is which.

------------------------------------------------------------------------------
AND THE QUESTION P4b ASKED OF alpha*, ASKED OF WHAT VERSION C ACTUALLY ADDED
------------------------------------------------------------------------------

P4b asked whether ``alpha*`` tracks quality or badness, and got an answer that does not
resolve: it agrees with regret and disagrees with the error volumes. ``alpha*`` is
model-internal, and Version C does not change it -- the cross-fit selects on the same half,
so ``alpha_star`` is bit-identical to Version B's.

**The quantity Version C did add is the selection bias**, and the same question is open
about it: does a campaign whose certificate is more anti-conservative also do worse on
regret, or on the error volume, or neither? That is asked here for the first time.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

#: `plate1_only` IS `lhs` at 48 wells -- the committed columns agree to 4.44e-16. Ranking
#: it separately makes `lhs` a second arm and shifts every rank below it. This was wrong in
#: the first cut of the Part IV headline and had to be redone.
NEVER_RANK = ("plate1_only",)

TAUS = (1.0, 1.1, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0)
N_BOOT, BOOT_SEED = 4_000, 0
MIN_PAIRS = 10


def _problems(rows: list[dict], key: str) -> dict[tuple, dict[str, float]]:
    """``(instance, seed) -> {arm: value}``, one entry per arm per problem."""
    out: dict[tuple, dict[str, float]] = collections.defaultdict(dict)
    for r in rows:
        if r["arm"] in NEVER_RANK:
            continue
        v = r.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        out[(r["instance"], int(r["seed"]))][r["arm"]] = float(v)
    return out


def mean_rank(rows: list[dict], key: str = "regret") -> dict[str, float]:
    """Mean rank of each arm, ranked **within a problem**, ties sharing the average rank.

    Within-problem because ranking pooled regrets would let an easy instance's loser
    outrank a hard instance's winner. Ties share the average rank because `lhs` and
    `plate1_only` agree to 4.44e-16 and a tie-break would invent an ordering the data does
    not contain.
    """
    acc: dict[str, list[float]] = collections.defaultdict(list)
    for _, per_arm in _problems(rows, key).items():
        order = sorted(per_arm.items(), key=lambda kv: kv[1])
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and order[j + 1][1] == order[i][1]:
                j += 1
            shared = (i + j) / 2 + 1          # 1-indexed average rank over the tie block
            for k in range(i, j + 1):
                acc[order[k][0]].append(shared)
            i = j + 1
    return {a: st.mean(v) for a, v in sorted(acc.items())}


def performance_profile(rows: list[dict], key: str = "regret",
                        taus=TAUS) -> dict[str, dict[float, float]]:
    """Dolan-More: fraction of problems where an arm is within ``tau`` x the best.

    **A best of exactly zero is handled without dividing by it.** Regret 0 is attainable --
    a planted design reaches it -- and a ratio would be `inf` or `nan`, silently dropping
    the problem from every arm's count rather than from none.
    """
    per_problem = _problems(rows, key)
    arms = sorted({a for d in per_problem.values() for a in d})
    hits = {a: {t: 0 for t in taus} for a in arms}
    totals = {a: 0 for a in arms}

    for per_arm in per_problem.values():
        best = min(per_arm.values())
        for a, v in per_arm.items():
            totals[a] += 1
            for t in taus:
                # `v <= t * best` throughout, which at best == 0 reduces to `v <= 0` --
                # exactly "this arm also achieved the best" -- with no division anywhere.
                if v <= t * best:
                    hits[a][t] += 1
    return {a: {t: (hits[a][t] / totals[a] if totals[a] else float("nan")) for t in taus}
            for a in arms}


def bias_correlation(rows: list[dict], against: str, alpha: float = 0.95,
                     n_boot: int = N_BOOT) -> dict:
    """Spearman rho between the **selection bias** and another column, bootstrap CI.

    ``nan`` bias rows are **dropped, not scored as zero**: a ``nan`` there means an EMPTY
    certificate, 54-69% of predictive regions are empty at some cells, and scoring the
    common row as zero would drag rho toward 0 and read as "no relationship".
    """
    key = f"ce_selection_bias_{alpha}"
    pairs = [(float(r[key]), float(r[against])) for r in rows
             if r.get(key) is not None and r.get(against) is not None
             and not math.isnan(float(r[key])) and not math.isnan(float(r[against]))]
    if len(pairs) < MIN_PAIRS:
        raise ValueError(f"only {len(pairs)} usable pairs for {key} vs {against}; "
                         f"need >= {MIN_PAIRS}")
    x = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])

    def _rho(a, b):
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        if ra.std() == 0 or rb.std() == 0:
            return float("nan")
        return float(np.corrcoef(ra, rb)[0, 1])

    rho = _rho(x, y)
    rng = np.random.default_rng(BOOT_SEED)
    boot = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), len(x))
        boot.append(_rho(x[idx], y[idx]))
    boot = np.array([b for b in boot if not math.isnan(b)])
    lo, hi = (np.percentile(boot, [2.5, 97.5]) if boot.size else (float("nan"),) * 2)
    return {"rho": rho, "ci_lo": float(lo), "ci_hi": float(hi), "n": len(pairs),
            "against": against, "alpha": alpha,
            "excludes_zero": bool(lo > 0 or hi < 0)}


def _load(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d["rows"] if isinstance(d, dict) else d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+",
                    default=[str(ROOT / "results" / "versionc-form1-s010.json"),
                             str(ROOT / "results" / "versionc-form1-s025.json")])
    args = ap.parse_args()

    payload = {"never_rank": list(NEVER_RANK), "taus": list(TAUS), "cells": {}}
    for f in args.files:
        path = Path(f)
        rows = _load(path)
        sigma = rows[0]["sigma"]
        # One row per (arm, instance, seed): the terminal metrics do not vary by cell.
        seen, terminal = set(), []
        for r in rows:
            k = (r["instance"], r["seed"], r["arm"])
            if k not in seen:
                seen.add(k)
                terminal.append(r)

        print(f"\n{'='*74}\nsigma = {sigma}   ({len(terminal)} arm-campaigns, "
              f"`plate1_only` excluded from every ranking)\n{'='*74}")

        ranks = {rule: mean_rank(terminal, key=col)
                 for rule, col in (("A", "regret"), ("P", "regret_p"))}
        print(f"\n{'arm':<22}{'mean rank A':>13}{'mean rank P':>13}{'move':>8}")
        for a in sorted(ranks["A"], key=lambda x: ranks["P"][x]):
            mv = ranks["A"][a] - ranks["P"][a]
            print(f"{a:<22}{ranks['A'][a]:>13.2f}{ranks['P'][a]:>13.2f}{mv:>+8.2f}")

        prof = {rule: performance_profile(terminal, key=col)
                for rule, col in (("A", "regret"), ("P", "regret_p"))}
        print(f"\nperformance profile, RULE P -- fraction of problems within tau x best")
        head = "".join(f"{t:>8}" for t in TAUS)
        print(f"{'arm':<22}{head}")
        for a in sorted(prof["P"], key=lambda x: -prof["P"][x][1.0]):
            print(f"{a:<22}" + "".join(f"{prof['P'][a][t]:>8.2f}" for t in TAUS))

        cors = {}
        for against in ("regret_p", "total_error_vol_pred"):
            try:
                cors[against] = bias_correlation(rows, against=against, alpha=0.95)
            except ValueError as e:
                cors[against] = {"error": str(e)}
        print(f"\nselection bias (alpha=0.95) vs:")
        for k, v in cors.items():
            if "error" in v:
                print(f"  {k:<24} {v['error']}")
            else:
                print(f"  {k:<24} rho {v['rho']:+.4f}  CI [{v['ci_lo']:+.4f}, "
                      f"{v['ci_hi']:+.4f}]  n={v['n']}  "
                      f"{'excludes 0' if v['excludes_zero'] else 'includes 0'}")

        payload["cells"][str(sigma)] = {
            "mean_rank": ranks, "performance_profile": prof,
            "bias_correlation": cors, "n_campaigns": len(terminal)}

    out = ROOT / "results" / "versionc-conventions.json"
    out.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out.name}")


if __name__ == "__main__":
    main()
