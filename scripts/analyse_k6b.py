"""K6b analysis: does the JOINT certification metric rank arms differently from regret?

Same registered decision as K6, and it gets no escape hatch of its own. Q20 §2 governs:
Wilcoxon decides yes/no, the instance bootstrap reports magnitude, disagreements are
reported rather than resolved.

`alpha*` is always defined, so unlike certified volume it never needs an empty-cell
exclusion. `ce_false_in_*` and `ce_contain_*` DO carry nan for empty CE_alpha, and those
are dropped pairwise with the dropped count printed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

IN = Path("results/k6b-conservative.json")
#: Spread arms, run separately. Without them K6b answers the same partial question K6's
#: first run did -- "is screening fatal" rather than "does a spread design certify better".
IN_SPREAD = Path("results/k6b-conservative-spread.json")
OUT = Path("results/k6b-analysis.json")
SPREAD, CLUSTERED = "doe", "qlogei"


def _paired(rows, a, b, key, tf):
    def pick(arm):
        return {(r["instance"], r["seed"]): r[key] for r in rows
                if r["arm"] == arm and r["tau_frac"] == tf}
    A, B = pick(a), pick(b)
    ks = sorted(set(A) & set(B))
    pa = np.array([A[k] for k in ks], float)
    pb = np.array([B[k] for k in ks], float)
    ok = ~(np.isnan(pa) | np.isnan(pb))
    return pa[ok], pb[ok], int((~ok).sum())


def _contrast(pa, pb, n_boot=4000, seed=0):
    if len(pa) < 3:
        return {"n": len(pa), "mean": float("nan"), "lo": float("nan"),
                "hi": float("nan"), "wilcoxon_p": float("nan")}
    d = pa - pb
    rng = np.random.default_rng(seed)
    boots = [rng.choice(d, len(d), replace=True).mean() for _ in range(n_boot)]
    try:
        p = float(wilcoxon(pa, pb).pvalue)
    except ValueError:
        p = 1.0
    return {"n": len(d), "mean": float(d.mean()),
            "lo": float(np.percentile(boots, 2.5)),
            "hi": float(np.percentile(boots, 97.5)), "wilcoxon_p": p}


def main() -> None:
    data = json.loads(IN.read_text())
    rows, cfg = data["rows"], data["config"]
    arms, tfs = list(cfg["arms"]), cfg["tau_fracs"]
    if IN_SPREAD.exists():
        extra = json.loads(IN_SPREAD.read_text())
        for k in ("dim", "sigma", "tau_fracs", "subset_n", "n_draws", "grid_seed"):
            assert extra["config"][k] == cfg[k], f"spread run disagrees on {k!r}"
        rows = rows + extra["rows"]
        arms = arms + [a for a in extra["config"]["arms"] if a not in arms]
        print(f"merged {len(extra['rows'])} spread rows "
              f"({', '.join(extra['config']['arms'])})")
    print(f"K6b · {len(rows)} rows · d={cfg['dim']} sigma={cfg['sigma']} · "
          f"gate failures {len(data['gate_failures'])}\n")

    regret = {a: float(np.mean([r["regret"] for r in rows
                                if r["arm"] == a and r["tau_frac"] == tfs[0]]))
              for a in arms}
    regret_rank = sorted(arms, key=lambda a: regret[a])
    print("REGRET (lower better): " + "  ".join(f"{a}={regret[a]:.4f}" for a in regret_rank))
    print(f"  ranking: {' < '.join(regret_rank)}\n")

    out = {"regret": regret, "regret_rank": regret_rank, "cells": []}
    print("ALPHA* (higher better) -- always defined, never empty:")
    print(f"{'tau_f':>6} {'theta':>6}  {'ranking':<52} {'match?':>7}")
    for tf in tfs:
        sub = [r for r in rows if r["tau_frac"] == tf]
        a_star = {a: float(np.mean([r["alpha_star"] for r in sub if r["arm"] == a]))
                  for a in arms}
        rank = sorted(arms, key=lambda a: -a_star[a])
        match = rank == regret_rank
        print(f"{tf:>6.2f} {sub[0]['theta']:>6.3f}  {' > '.join(rank):<52} {str(match):>7}")
        print(f"       " + "  ".join(f"{a}={a_star[a]:.3f}" for a in rank))
        out["cells"].append({"tau_frac": tf, "alpha_star": a_star,
                             "rank": rank, "matches_regret_rank": bool(match)})

    print(f"\n{SPREAD} - {CLUSTERED} on alpha*, paired (positive favours {SPREAD}):")
    for tf in tfs:
        pa, pb, dr = _paired(rows, SPREAD, CLUSTERED, "alpha_star", tf)
        c = _contrast(pa, pb)
        star = "  *" if c["wilcoxon_p"] < 0.05 else ""
        print(f"  tau_f={tf:.2f}: n={c['n']:3d} mean={c['mean']:+.4f} "
              f"[{c['lo']:+.4f},{c['hi']:+.4f}] p={c['wilcoxon_p']:.4f}{star}")
        out.setdefault("spread_vs_clustered", []).append({"tau_frac": tf, **c})

    print("\nA1 -- Q30's additive kernel. Regret said 0.0015, p=0.71. On alpha*:")
    for add in ("qlogei-add", "qlogei-addonly"):
        if add not in arms:
            continue
        for tf in tfs:
            pa, pb, _ = _paired(rows, add, "qlogei", "alpha_star", tf)
            c = _contrast(pa, pb)
            star = "  *" if c["wilcoxon_p"] < 0.05 else ""
            print(f"  {add:15s} tau_f={tf:.2f} mean={c['mean']:+.4f} "
                  f"[{c['lo']:+.4f},{c['hi']:+.4f}] p={c['wilcoxon_p']:.4f}{star}")
            out.setdefault("a1", {}).setdefault(add, []).append({"tau_frac": tf, **c})

    print("\nCE_alpha emptiness and ACTUAL containment (nominal vs achieved):")
    for a in cfg["alphas"]:
        print(f"  alpha={a}:")
        for arm in arms:
            sub = [r for r in rows if r["arm"] == arm]
            emp = float(np.mean([r[f"ce_empty_{a}"] for r in sub]))
            fi = np.array([r[f"ce_false_in_{a}"] for r in sub], float)
            ct = np.array([r[f"ce_contain_{a}"] for r in sub], float)
            print(f"    {arm:15s} empty={emp:5.0%}  "
                  f"false_in={np.nanmean(fi) if np.isfinite(fi).any() else float('nan'):.4f}  "
                  f"contain={np.nanmean(ct) if np.isfinite(ct).any() else float('nan'):.4f}")
            out.setdefault("ce", {}).setdefault(str(a), {})[arm] = {
                "empty_frac": emp,
                "false_in": float(np.nanmean(fi)) if np.isfinite(fi).any() else None,
                "containment": float(np.nanmean(ct)) if np.isfinite(ct).any() else None}

    n_match = sum(c["matches_regret_rank"] for c in out["cells"])
    print(f"\nVERDICT INPUT: alpha* ranking matches regret ranking in "
          f"{n_match}/{len(out['cells'])} thresholds")
    OUT.write_text(json.dumps(out, indent=2))
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
