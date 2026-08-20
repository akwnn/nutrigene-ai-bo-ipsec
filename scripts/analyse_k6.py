"""K6 analysis: does the design-space ranking match the regret ranking?

The registered decision. If the arm ranking on the primary metric matches the ranking on
simple regret, the reframe adds nothing and SPADE Stages 4-5 are dropped. If it diverges
with the spread arm ahead, Version B is built. If it diverges with the clustered arm
ahead, that is a different paper.

Q20 §2 governs the statistics: **Wilcoxon decides yes/no, the instance bootstrap reports
magnitude, and disagreements are reported rather than resolved.**

Empty regions are counted, never averaged. `nan` from `iou` / `false_inclusion_rate`
means "nothing was claimed", which is not the same as a score of zero and must not be
allowed to average into one.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

IN = Path("results/k6-designspace.json")
OUT = Path("results/k6-analysis.json")
SPREAD, CLUSTERED = "doe", "qlogei"


def _paired(rows, arm_a, arm_b, key, gamma=None, tau_frac=None):
    """Paired (instance, seed) values for two arms. Pairs with nan on either side drop."""
    def pick(arm):
        return {(r["instance"], r["seed"]): r[key] for r in rows
                if r["arm"] == arm
                and (gamma is None or r["gamma"] == gamma)
                and (tau_frac is None or r["tau_frac"] == tau_frac)}
    a, b = pick(arm_a), pick(arm_b)
    keys = sorted(set(a) & set(b))
    pa = np.array([a[k] for k in keys], dtype=float)
    pb = np.array([b[k] for k in keys], dtype=float)
    ok = ~(np.isnan(pa) | np.isnan(pb))
    return pa[ok], pb[ok], int((~ok).sum())


def _contrast(pa, pb, n_boot=4000, seed=0):
    """Mean difference (a - b), its bootstrap CI, and the Wilcoxon p."""
    if len(pa) < 3:
        return {"n": len(pa), "mean": float("nan"), "lo": float("nan"),
                "hi": float("nan"), "wilcoxon_p": float("nan")}
    d = pa - pb
    rng = np.random.default_rng(seed)
    boots = [rng.choice(d, len(d), replace=True).mean() for _ in range(n_boot)]
    try:
        p = float(wilcoxon(pa, pb).pvalue)
    except ValueError:                       # all differences identically zero
        p = 1.0
    return {"n": len(d), "mean": float(d.mean()),
            "lo": float(np.percentile(boots, 2.5)),
            "hi": float(np.percentile(boots, 97.5)), "wilcoxon_p": p}


def main() -> None:
    data = json.loads(IN.read_text())
    rows = data["rows"]
    cfg = data["config"]
    arms = cfg["arms"]
    print(f"K6 analysis · {len(rows)} rows · d={cfg['dim']} sigma={cfg['sigma']}")
    print(f"gate failures in the source run: {len(data['gate_failures'])}\n")

    # --- regret ranking, which the design space is being compared against -------------
    regret = {a: np.mean([r["regret"] for r in rows
                          if r["arm"] == a and r["gamma"] == cfg["gammas"][0]
                          and r["tau_frac"] == cfg["tau_fracs"][0]]) for a in arms}
    regret_rank = sorted(arms, key=lambda a: regret[a])
    print("REGRET (lower better):")
    for a in regret_rank:
        print(f"  {a:15s} {regret[a]:.4f}")
    print(f"  ranking: {' < '.join(regret_rank)}\n")

    out = {"regret": regret, "regret_rank": regret_rank, "cells": [], "a1": {}}

    # --- per (gamma, tau_frac): the map ranking, and whether it matches ----------------
    print(f"{'gamma':>5} {'tauF':>5} {'tau':>6} "
          f"{'AUCpred rank':<46} {'match?':>7} {'empty':>7} {'FI@pred':>8}")
    for gamma in cfg["gammas"]:
        for tf in cfg["tau_fracs"]:
            sub = [r for r in rows if r["gamma"] == gamma and r["tau_frac"] == tf]
            if not sub:
                continue
            tau = sub[0]["tau"]
            auc = {}
            for a in arms:
                v = np.array([r["auc_pred"] for r in sub if r["arm"] == a], dtype=float)
                auc[a] = float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
            rank = sorted([a for a in arms if not np.isnan(auc[a])],
                          key=lambda a: -auc[a])
            match = (rank == [a for a in regret_rank if a in rank])
            empty = float(np.mean([r["empty_pred"] for r in sub]))
            fi = np.array([r["fi_pred"] for r in sub], dtype=float)
            fi_m = float(np.nanmean(fi)) if np.isfinite(fi).any() else float("nan")
            print(f"{gamma:>5.2f} {tf:>5.2f} {tau:>6.3f} "
                  f"{' > '.join(rank):<46} {str(match):>7} {empty:>6.0%} {fi_m:>8.3f}")
            out["cells"].append({"gamma": gamma, "tau_frac": tf, "tau": tau,
                                 "auc_pred": auc, "auc_rank": rank,
                                 "matches_regret_rank": bool(match),
                                 "empty_frac": empty, "false_inclusion_pred": fi_m})

    # --- the headline contrast: spread vs clustered on the map -------------------------
    print(f"\n{SPREAD} - {CLUSTERED}, paired, per cell "
          f"(AUC: positive favours {SPREAD}):")
    for gamma in cfg["gammas"]:
        for tf in cfg["tau_fracs"]:
            pa, pb, dropped = _paired(rows, SPREAD, CLUSTERED, "auc_pred", gamma, tf)
            c = _contrast(pa, pb)
            star = "  *" if c["wilcoxon_p"] < 0.05 else ""
            print(f"  gamma={gamma:.2f} tauF={tf:.2f}: n={c['n']:3d} "
                  f"mean={c['mean']:+.4f} [{c['lo']:+.4f},{c['hi']:+.4f}] "
                  f"p={c['wilcoxon_p']:.4f} dropped(nan)={dropped}{star}")
            out.setdefault("spread_vs_clustered", []).append(
                {"gamma": gamma, "tau_frac": tf, "dropped_nan": dropped, **c})

    # --- A1: Q30's kernel arms, regret vs map ------------------------------------------
    print("\nA1 -- Q30's additive kernel: regret said 0.0015, p=0.71. On the map:")
    for add in ("qlogei-add", "qlogei-addonly"):
        if add not in arms:
            continue
        pr_a, pr_b, _ = _paired(rows, add, "qlogei", "regret",
                                cfg["gammas"][0], cfg["tau_fracs"][0])
        cr = _contrast(pr_a, pr_b)
        pa, pb, _ = _paired(rows, add, "qlogei", "auc_pred", 0.90, 0.75)
        cm = _contrast(pa, pb)
        print(f"  {add:15s} regret {cr['mean']:+.4f} [{cr['lo']:+.4f},{cr['hi']:+.4f}] "
              f"p={cr['wilcoxon_p']:.4f}")
        print(f"  {'':15s} AUC    {cm['mean']:+.4f} [{cm['lo']:+.4f},{cm['hi']:+.4f}] "
              f"p={cm['wilcoxon_p']:.4f}   (gamma=0.90, tauF=0.75)")
        out["a1"][add] = {"regret": cr, "auc_pred": cm}

    # --- the free finding: is nominal 95% anti-conservative? ---------------------------
    print("\nFalse-inclusion rate of the nominal-95% region (target 0.05):")
    for a in arms:
        fp = np.array([r["fi_pred"] for r in rows
                       if r["arm"] == a and r["gamma"] == 0.95], dtype=float)
        fl = np.array([r["fi_latent"] for r in rows
                       if r["arm"] == a and r["gamma"] == 0.95], dtype=float)
        n_emp = int(np.isnan(fp).sum())
        print(f"  {a:15s} predictive={np.nanmean(fp) if np.isfinite(fp).any() else float('nan'):.4f}  "
              f"latent={np.nanmean(fl) if np.isfinite(fl).any() else float('nan'):.4f}  "
              f"(empty cells excluded: {n_emp})")
        out.setdefault("false_inclusion_95", {})[a] = {
            "predictive": float(np.nanmean(fp)) if np.isfinite(fp).any() else None,
            "latent": float(np.nanmean(fl)) if np.isfinite(fl).any() else None,
            "empty_excluded": n_emp}

    n_match = sum(c["matches_regret_rank"] for c in out["cells"])
    print(f"\nVERDICT INPUT: map ranking matches regret ranking in "
          f"{n_match}/{len(out['cells'])} cells")
    OUT.write_text(json.dumps(out, indent=2))
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
