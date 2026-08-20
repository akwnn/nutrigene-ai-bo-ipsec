"""Version B analysis: does a second plate close the gap to qLogNEI?

Two registered kills, and neither gets an escape hatch:
  * plate 2 does not close the map / alpha* gap to qLogNEI  -> SPADE is dead
  * plate 2 does not beat 8 RANDOM wells                     -> the criterion is not
    earning its place; the honest result is "a second plate helps, the criterion does not"

Reported on BOTH axes. Every K6 contrast was at equal wells only; Version B is 2 rounds
against qLogNEI's 10, and that is half the claim.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon

IN = Path("results/versionb.json")


def paired(rows, a, b, key):
    P = lambda arm: {(r["instance"], r["seed"]): r[key] for r in rows if r["arm"] == arm}
    A, B = P(a), P(b); ks = sorted(set(A) & set(B))
    pa = np.array([A[k] for k in ks], float); pb = np.array([B[k] for k in ks], float)
    ok = ~(np.isnan(pa) | np.isnan(pb)); return pa[ok], pb[ok]


def con(pa, pb, seed=0):
    if len(pa) < 3: return None
    d = pa - pb; rng = np.random.default_rng(seed)
    b = [rng.choice(d, len(d), replace=True).mean() for _ in range(4000)]
    try: p = float(wilcoxon(pa, pb).pvalue)
    except ValueError: p = 1.0
    return d.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5), p, len(d)


def line(rows, a, b, key, label):
    c = con(*paired(rows, a, b, key))
    if c is None: return f"  {label:34s} insufficient pairs"
    return (f"  {label:34s} {c[0]:+.4f} [{c[1]:+.4f},{c[2]:+.4f}] "
            f"p={c[3]:.4f}{'  *' if c[3] < 0.05 else ''}")


def main():
    d = json.loads(IN.read_text()); rows, cfg = d["rows"], d["config"]
    arms = ["versionb", "versionb_random", "plate1_only", "doe", "qlognei"]
    print(f"Version B · {len(rows)} rows · {cfg['n_plate1']}+{cfg['n_plate2']} wells\n")

    print(f"{'arm':17s} {'rounds':>6} {'wells':>6} {'regret':>8}  " +
          "  ".join(f"a*@{tf}" for tf in cfg["tau_fracs"]))
    for a in arms:
        sub = [r for r in rows if r["arm"] == a]
        if not sub: continue
        print(f"{a:17s} {sub[0]['rounds']:>6} {sub[0]['n_wells']:>6} "
              f"{np.mean([r['regret'] for r in sub]):>8.4f}  " +
              "  ".join(f"{np.mean([r[f'alpha_star_{tf}'] for r in sub]):.3f} "
                        for tf in cfg["tau_fracs"]))

    print("\nKILL 1 -- does plate 2 close the gap to qLogNEI? (positive favours versionb)")
    for tf in cfg["tau_fracs"]:
        print(line(rows, "versionb", "qlognei", f"alpha_star_{tf}", f"alpha* @ tau_f={tf}"))
    for tf in cfg["tau_fracs"]:
        print(line(rows, "versionb", "qlognei", f"auc_{tf}", f"AUC    @ tau_f={tf}"))

    print("\nKILL 2 -- does the LSE criterion beat 8 RANDOM wells?")
    for tf in cfg["tau_fracs"]:
        print(line(rows, "versionb", "versionb_random", f"alpha_star_{tf}",
                   f"alpha* @ tau_f={tf}"))

    print("\nDoes a second plate help at all? (versionb - plate1_only, both 48 wells)")
    for tf in cfg["tau_fracs"]:
        print(line(rows, "versionb", "plate1_only", f"alpha_star_{tf}",
                   f"alpha* @ tau_f={tf}"))
    print(line(rows, "versionb", "plate1_only", "regret", "regret (negative = better)"))


if __name__ == "__main__":
    main()
