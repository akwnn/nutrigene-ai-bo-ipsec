"""Amendment E, phase 1.1 + 1.5: did targeting the DELIVERABLE's boundary help?

Three questions, and the third governs the other two:

  E6  `versionb_predictive` vs `versionb` on AUC (VALIDATED -- it consults the noiseless
      oracle), alpha* (MODEL-INTERNAL -- a functional of the fitted posterior and nothing
      else) and empirical containment (VALIDATED). Section 1.4 of the technical report:
      where a validated and a model-internal metric disagree, the validated one wins and
      the disagreement is reported, not resolved.

  E1  the distribution of `acq_cv = SD(a)/|mean(a)|` and how many campaigns fall below
      the threshold registered at `d624fa2` from the Matern 5/2 kernel. Below it a
      campaign reports "acquisition uninformative at this density" instead of
      contributing a silent null to the KILL 2 contrast.

  E2  how often the exclusion radius actually bound, which E2 asserted was never.

Statistics as registered: unit `(instance, seed)`, n = 50, paired; 4,000-resample
percentile bootstrap of the paired differences (`default_rng(0)`); two-sided Wilcoxon on
the same pairs; Holm within each metric family; SESOI 0.02. Wilcoxon governs yes/no, the
bootstrap reports magnitude, and **disagreements are reported, not resolved**.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

BOOT, SESOI, RNG_SEED = 4000, 0.02, 0


def paired(rows, a, b, key):
    P = lambda arm: {(r["instance"], r["seed"]): r[key] for r in rows if r["arm"] == arm}
    A, B = P(a), P(b)
    ks = sorted(set(A) & set(B))
    pa = np.array([A[k] for k in ks], float)
    pb = np.array([B[k] for k in ks], float)
    ok = ~(np.isnan(pa) | np.isnan(pb))
    return pa[ok], pb[ok]


def contrast(pa, pb):
    """Mean paired difference, percentile bootstrap interval, Wilcoxon p, n."""
    if len(pa) < 3:
        return None
    d = pa - pb
    rng = np.random.default_rng(RNG_SEED)
    boot = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(BOOT)])
    try:
        p = float(wilcoxon(pa, pb).pvalue)
    except ValueError:                 # all differences exactly zero
        p = 1.0
    return dict(mean=float(d.mean()), lo=float(np.percentile(boot, 2.5)),
                hi=float(np.percentile(boot, 97.5)), p=p, n=int(len(d)))


def holm(cells):
    """Holm-Bonferroni across a family. Returns {label: adjusted p}."""
    order = sorted(cells, key=lambda k: cells[k]["p"])
    m, adj, running = len(order), {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * cells[k]["p"]))
        adj[k] = running
    return adj


def family(rows, a, b, keys, label, title):
    print(f"\n{title}   (positive favours {a})")
    cells = {}
    for k, lab in keys:
        c = contrast(*paired(rows, a, b, k))
        if c is not None:
            cells[lab] = c
    if not cells:
        print("  insufficient pairs")
        return
    adj = holm(cells)
    print(f"  {'cell':16s} {'mean':>9} {'95% bootstrap':>22} {'wilcoxon':>10} "
          f"{'holm':>8} {'n':>4}  flags")
    for lab, c in cells.items():
        flags = []
        if (c["p"] < 0.05) != (c["lo"] > 0 or c["hi"] < 0):
            flags.append("BOOT/WILCOXON DISAGREE")
        if adj[lab] < 0.05:
            flags.append("holm-significant")
        if abs(c["mean"]) < SESOI:
            flags.append(f"|effect| < SESOI {SESOI}")
        print(f"  {lab:16s} {c['mean']:>+9.4f} [{c['lo']:>+8.4f},{c['hi']:>+8.4f}] "
              f"{c['p']:>10.4f} {adj[lab]:>8.4f} {c['n']:>4}  {'; '.join(flags)}")


def containment(rows, arms, tau_fracs, alphas):
    """The VALIDATED guarantee: fraction of NON-EMPTY certified sets inside the truth.

    Empty sets are excluded, never counted as successes -- an empty set is vacuously
    contained and counting it would inflate the rate with campaigns that certified
    nothing. `n` therefore differs per cell and the fractions are never pooled.
    """
    print("\nEMPIRICAL CONTAINMENT (VALIDATED against ground truth) -- must be >= alpha")
    failures = []
    for tf in tau_fracs:
        print(f"\n  tau_frac = {tf}")
        print(f"  {'arm':22s} " + "  ".join(f"alpha={a:<16}" for a in alphas))
        for arm in arms:
            cells = []
            for a in alphas:
                v = [r[f"ce_empirical_{tf}_{a}"] for r in rows if r["arm"] == arm]
                v = [x for x in v if not (x is None or math.isnan(x))]
                if not v:
                    cells.append(f"{'-- all empty --':<22}")
                    continue
                frac = sum(v) / len(v)
                bad = frac < a
                if bad:
                    failures.append((arm, tf, a, frac, len(v)))
                cells.append(f"{frac:.3f} ({int(sum(v)):>2}/{len(v):<2}){' FAIL' if bad else '    '}"
                             .ljust(22))
            print(f"  {arm:22s} " + "  ".join(cells))
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results/versionb-predictive.json"))
    args = ap.parse_args()
    d = json.loads(args.results.read_text())
    rows, cfg, prov = d["rows"], d["config"], d["provenance"]
    tfs, alphas = cfg["tau_fracs"], cfg["alphas"]
    arms = cfg["arms"]

    print(f"Amendment E phase 1.1 + 1.5 · {len(rows)} rows · {cfg['n_plate1']}+"
          f"{cfg['n_plate2']} wells · sha {prov['git_sha'][:7]}")
    print(f"gate: {prov['gate_rows_checked']} comparisons against {prov['gate_file']}, "
          f"{len(prov['gate_failures'])} failures")

    print(f"\n{'arm':22s} {'rounds':>6} {'regret':>8}  " +
          "  ".join(f"AUC@{tf}" for tf in tfs) + "   " +
          "  ".join(f"a*@{tf}" for tf in tfs))
    for a in arms:
        sub = [r for r in rows if r["arm"] == a]
        if not sub:
            continue
        print(f"{a:22s} {sub[0]['rounds']:>6} "
              f"{np.mean([r['regret'] for r in sub]):>8.4f}  " +
              "  ".join(f"{np.nanmean([r[f'auc_{tf}'] for r in sub]):.4f} " for tf in tfs) +
              "  " +
              "  ".join(f"{np.mean([r[f'alpha_star_{tf}'] for r in sub]):.3f} " for tf in tfs))

    # ---- E1: flatness -------------------------------------------------------------
    thr = cfg["acq_cv_flat"]
    print(f"\n{'='*78}\nE1 — ACQUISITION FLATNESS.  registered threshold acq_cv < {thr}")
    for arm in ("versionb", "versionb_predictive"):
        cv = np.array([r["acq_cv"] for r in rows
                       if r["arm"] == arm and r.get("acq_cv") is not None], float)
        if not cv.size:
            continue
        below = int((cv < thr).sum())
        print(f"  {arm:22s} n={cv.size}  min {cv.min():.4f}  p05 {np.percentile(cv,5):.4f}  "
              f"median {np.median(cv):.4f}  p95 {np.percentile(cv,95):.4f}  "
              f"max {cv.max():.4f}")
        print(f"  {'':22s} below threshold: {below}/{cv.size}"
              + ("  -> acquisition uninformative at this density" if below else
                 "  -> NO campaign is flat; E1's worry is not what diluted KILL 2"))

    # ---- E2: exclusion ------------------------------------------------------------
    print(f"\n{'='*78}\nE2 — DID THE EXCLUSION RADIUS BIND?")
    for arm in ("versionb", "versionb_predictive"):
        sub = [r for r in rows if r["arm"] == arm and r.get("excl_bound") is not None]
        if not sub:
            continue
        b = sum(r["excl_bound"] for r in sub)
        print(f"  {arm:22s} bound in {b}/{len(sub)} campaigns · radius median "
              f"{np.median([r['excl_radius'] for r in sub]):.4f} · top-q min cheb median "
              f"{np.median([r['topq_min_cheb'] for r in sub]):.4f} · achieved min cheb "
              f"median {np.median([r['plate2_min_cheb'] for r in sub]):.4f}")
    rnd = [r["plate2_min_cheb"] for r in rows if r["arm"] == "versionb_random"]
    if rnd:
        print(f"  {'versionb_random':22s} (no criterion, no exclusion) achieved min cheb "
              f"median {np.median(rnd):.4f}")

    # ---- E6: the predictive straddle ----------------------------------------------
    print(f"\n{'='*78}\nE6 — PREDICTIVE STRADDLE vs THE PUBLISHED LATENT ONE")
    family(rows, "versionb_predictive", "versionb",
           [(f"auc_{tf}", f"AUC @ {tf}") for tf in tfs], "auc",
           "AUC  [VALIDATED — consults the noiseless oracle]")
    family(rows, "versionb_predictive", "versionb",
           [(f"alpha_star_{tf}", f"alpha* @ {tf}") for tf in tfs], "astar",
           "alpha*  [MODEL-INTERNAL — a functional of the fitted posterior only]")
    family(rows, "versionb_predictive", "versionb",
           [("regret", "regret")], "regret",
           "regret  [VALIDATED — positive means the predictive arm is WORSE]")

    print(f"\n{'='*78}")
    failures = containment(rows, arms, tfs, alphas)

    print(f"\n{'='*78}\nSTOP-CONDITION CHECK")
    vb = [f for f in failures if f[0] == "versionb"]
    print(f"  versionb below nominal anywhere: {'YES -- STOP' if vb else 'no'}")
    for f in vb:
        print(f"    {f}")
    print(f"  gate failures: {len(prov['gate_failures'])}")
    others = [f for f in failures if f[0] != "versionb"]
    if others:
        print("  other arms below nominal (reported, not a stop condition):")
        for f in others:
            print(f"    arm={f[0]} tau_frac={f[1]} alpha={f[2]} -> {f[3]:.3f} (n={f[4]})")


if __name__ == "__main__":
    main()
