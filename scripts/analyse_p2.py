"""P2 analysis: the gamma ladder, the containment table, and the one gate Version B has.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION".

THE THREE THINGS THIS FILE REFUSES TO DO
----------------------------------------
1. **Rank `plate1_only` as a separate arm.** It IS `lhs` -- the two committed columns
   agree to a worst |delta| of 4.44e-16 (D23.1). It is reported beside `lhs`, and
   neither is double-counted. :data:`RANKED_ARMS` is the three two-plate arms and
   nothing else.
2. **Average empirical containment across cells.** It is a fraction of **non-empty**
   certified sets, so every cell has a different denominator; pooling 47/50 with 7/8
   would produce a number that is not a rate of anything. Each cell reports its own
   ``n``, and a cell with ``n = 0`` reports no verdict at all -- certifying nothing is
   not a failed certificate.
3. **Resolve a disagreement between the Wilcoxon and the bootstrap.** Per Q20 §2 the
   Wilcoxon governs yes/no, the bootstrap reports magnitude, and disagreements are
   REPORTED. `disagrees` is a column, not a branch.

Metric status travels with every number. VALIDATED (consults the noiseless oracle):
regret, AUC, Brier, IoU, empirical containment, false-inclusion, ``sup_err``,
``grid_r2``. MODEL-INTERNAL (a functional of the fitted posterior and nothing else):
``alpha_star``, ``vorobev_deviation``, ``ce_contain``. A validated metric beats a
model-internal one and the disagreement is reported.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results" / "p2-versionb-gamma.json"
#: The committed `lhs` rows: the gate target, and the arm `plate1_only` IS.
SPREAD = ROOT / "results" / "k6-designspace-spread.json"

#: D23.1. `plate1_only` is NOT here, and must never be.
RANKED_ARMS = ("versionb", "versionb_random", "versionb_predictive")
#: Everything that appears in a table. `plate1_only` is reported, never ranked.
REPORTED_ARMS = ("versionb", "versionb_random", "versionb_predictive", "plate1_only")

#: Amendment E, restated so no reader has to go looking.
N_BOOT, BOOT_SEED, SESOI = 4000, 0, 0.02
ALPHAS = (0.50, 0.80, 0.95)

#: Which side of the VALIDATED / MODEL-INTERNAL line each metric sits on.
STATUS = {"regret": "VALIDATED", "auc_pred": "VALIDATED", "auc_latent": "VALIDATED",
          "brier_pred": "VALIDATED", "brier_latent": "VALIDATED",
          "iou_pred": "VALIDATED", "iou_latent": "VALIDATED",
          "fi_pred": "VALIDATED", "fi_latent": "VALIDATED",
          "sup_err": "VALIDATED", "grid_r2": "VALIDATED",
          "ce_empirical": "VALIDATED",
          "alpha_star": "MODEL-INTERNAL", "vorobev_deviation": "MODEL-INTERNAL",
          "ce_contain": "MODEL-INTERNAL (circular -- CE selects on it)",
          "vol_pred": "descriptive", "empty_pred": "descriptive",
          "box_vol_pred": "descriptive"}


# ----------------------------------------------------------------------- statistics


def holm(pvalues) -> list[float]:
    """Holm-Bonferroni adjusted p, in the input order. Monotone, capped at 1.0."""
    ps = list(pvalues)
    if not ps:
        return []
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, running)
    return adj


def paired(rows, arm_a, arm_b, key, gamma=None, tau_frac=None):
    """Paired ``(instance, seed)`` values. Pairs with nan on either side drop, counted."""
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


def contrast(pa, pb, n_boot=N_BOOT, seed=BOOT_SEED) -> dict:
    """Mean paired difference, 4,000-resample percentile CI, two-sided Wilcoxon.

    The two are reported side by side and never reconciled: `wilcoxon_p` decides yes/no,
    `[lo, hi]` reports magnitude, and `disagrees` records when they point different ways.
    """
    if len(pa) < 3:
        return {"n": int(len(pa)), "mean": float("nan"), "lo": float("nan"),
                "hi": float("nan"), "wilcoxon_p": float("nan"),
                "disagrees": False, "within_sesoi": False}
    d = pa - pb
    rng = np.random.default_rng(seed)
    boots = [rng.choice(d, len(d), replace=True).mean() for _ in range(n_boot)]
    try:
        p = float(wilcoxon(pa, pb).pvalue)
    except ValueError:                       # every difference identically zero
        p = 1.0
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    ci_excludes_zero = (lo > 0) or (hi < 0)
    return {"n": int(len(d)), "mean": float(d.mean()), "lo": lo, "hi": hi,
            "wilcoxon_p": p, "disagrees": bool((p < 0.05) != ci_excludes_zero),
            "within_sesoi": bool(abs(float(d.mean())) < SESOI)}


# ------------------------------------------------------- the registered kill's table


def containment_table(rows, alphas=ALPHAS, arm=None) -> list[dict]:
    """Empirical containment per (arm, gamma, tau_frac, alpha), each with its own ``n``.

    ``n`` counts **non-empty** certified sets only. An empty set is vacuously contained
    and `run_p2_versionb_gamma.vorobev_columns` writes ``nan`` for it; counting it as a
    success would inflate the rate with campaigns that certified nothing.

    ``below_nominal`` is ``None`` when ``n == 0``. Nothing was certified, so the
    certificate made no claim that could fail -- which is not the same as a claim that
    held, and must not be reported as one.

    ``true_frac`` travels with every cell because **containment is not equally hard
    along the ladder, and it gets EASIER as gamma rises, not harder.** gamma enters tau
    through ``tau_max`` multiplicatively, so gamma = 0.99 gives ``tau_max = 0.4184`` and
    an absolute threshold of 0.251 at ``tau_frac = 0.60`` -- at which the true superlevel
    set covers **0.99916** of the box (measured on the committed `lhs` rows). A set
    certified there is contained almost whatever it is. The hard corner is gamma = 0.50,
    ``tau_frac`` 0.85-0.95, where the true set covers 0.06844 and 0.00294. A containment
    fraction read without ``true_frac`` beside it says nothing about the certificate.
    """
    cells: dict[tuple, dict] = {}
    for r in rows:
        if arm is not None and r["arm"] != arm:
            continue
        for a in alphas:
            key = (r["arm"], r["gamma"], r["tau_frac"], a)
            c = cells.setdefault(key, {"arm": r["arm"], "gamma": r["gamma"],
                                       "tau_frac": r["tau_frac"], "alpha": a,
                                       "n": 0, "contained": 0, "n_empty": 0,
                                       "n_campaigns": 0, "_true": [], "_vol": []})
            c["n_campaigns"] += 1
            if "true_frac_above_tau" in r:
                c["_true"].append(float(r["true_frac_above_tau"]))
            if r[f"ce_empty_{a}"]:
                c["n_empty"] += 1
                continue
            v = r[f"ce_empirical_{a}"]
            if isinstance(v, float) and math.isnan(v):
                c["n_empty"] += 1
                continue
            c["n"] += 1
            c["contained"] += int(bool(v))
            c["_vol"].append(float(r.get(f"ce_vol_{a}", float("nan"))))
    out = []
    for key in sorted(cells):
        c = cells[key]
        c["fraction"] = c["contained"] / c["n"] if c["n"] else float("nan")
        c["below_nominal"] = None if c["n"] == 0 else bool(c["fraction"] < c["alpha"])
        c["true_frac"] = float(np.mean(c.pop("_true"))) if c["_true"] else float("nan")
        vol = c.pop("_vol")
        c["ce_vol"] = float(np.mean(vol)) if vol else float("nan")
        out.append(c)
    return out


def _fmt(v, width=7, prec=4):
    if v is None:
        return f"{'-':>{width}}"
    if isinstance(v, float) and math.isnan(v):
        return f"{'nan':>{width}}"
    return f"{v:>{width}.{prec}f}"


# ------------------------------------------------------------------------- printing


def _print_gate(data) -> None:
    gate, fails = data["gate"], data["gate_failures"]
    print("=" * 78)
    print("THE ONE GATE VERSION B HAS")
    print("=" * 78)
    print(gate["note"])
    print(f"\n  arm            : {gate['arm']} (regenerated through replay.regenerate "
          f"as `lhs`, so the 20-ordering arithmetic matches)")
    print(f"  tolerance      : {gate['tol']}  -- exact. One ULP is a failure.")
    print(f"  comparisons    : {gate['rows_checked']} rows x "
          f"{len(gate['columns'])} columns = "
          f"{gate['rows_checked'] * len(gate['columns'])}")
    print(f"  gate_failures  : {len(fails)}")
    if fails:
        for f in fails[:10]:
            print(f"    !! {f['instance']} seed={f['seed']} gamma={f['gamma']} "
                  f"tau_frac={f['tau_frac']}: "
                  + ", ".join(f"{b['column']} delta={b['abs_delta']:.3e}"
                              for b in f["failures"][:4]))
        print("\n  *** STOP CONDITION 1. Results are NOT comparable. ***")
    else:
        print("    every column of every cell reproduced at exactly 0.0")

    det = data["determinism"]
    print(f"\n  {det['what_it_is']}")
    checks = det["checks"]
    if checks:
        exact = [c for c in checks if c["exact_mu_max"]]
        worst_all = max(c["worst_abs_delta"] for c in checks)
        print(f"    {len(checks)} campaigns checked, worst |delta| = {worst_all:.3e}")
        if exact:
            we = max(c["worst_abs_delta"] for c in exact)
            print(f"    of those, {len(exact)} where optimum_value is exactly 1.0 "
                  f"(so the committed theta and this tau coincide bitwise): "
                  f"worst |delta| = {we:.3e}")
        reg = max(c["per_column"].get("regret", 0.0) for c in checks)
        print(f"    regret alone, which carries no tau at all: "
              f"worst |delta| = {reg:.3e}")
    else:
        print("    no committed Version B rows were available to check against")


def _print_ladder(rows, cfg) -> None:
    print("\n" + "=" * 78)
    print("THE GAMMA LADDER — the region metrics Version B has never had")
    print("=" * 78)
    print("VALIDATED: iou_pred, fi_pred, auc_pred.  "
          "MODEL-INTERNAL: alpha_star, ce_contain.\n")
    for arm in REPORTED_ARMS:
        sub0 = [r for r in rows if r["arm"] == arm]
        if not sub0:
            continue
        tag = "GATED (= lhs)" if arm == "plate1_only" else "UNGATABLE"
        print(f"--- {arm}  [{tag}]  "
              f"sup_err={np.mean([r['sup_err'] for r in sub0]):.4f} "
              f"grid_r2={np.mean([r['grid_r2'] for r in sub0]):.4f} "
              f"regret={np.mean([r['regret'] for r in sub0]):.4f}")
        print(f"  {'gamma':>5} {'tauF':>5} {'tau':>7} {'iou_pred':>9} {'fi_pred':>8} "
              f"{'vol_pred':>9} {'empty%':>7} {'auc_pred':>9} {'alpha*':>7}")
        for g in cfg["gammas"]:
            for tf in cfg["tau_fracs"]:
                sub = [r for r in sub0 if r["gamma"] == g and r["tau_frac"] == tf]
                if not sub:
                    continue
                def nm(k):
                    v = np.array([r[k] for r in sub], dtype=float)
                    return float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
                print(f"  {g:>5.2f} {tf:>5.2f} {sub[0]['tau']:>7.4f} "
                      f"{_fmt(nm('iou_pred'), 9)} {_fmt(nm('fi_pred'), 8)} "
                      f"{_fmt(nm('vol_pred'), 9)} "
                      f"{np.mean([r['empty_pred'] for r in sub]):>6.0%} "
                      f"{_fmt(nm('auc_pred'), 9)} {_fmt(nm('alpha_star'), 7)}")
        print()


def _print_containment(rows, cfg) -> None:
    print("=" * 78)
    print("THE REGISTERED KILL — empirical containment, the NON-circular check")
    print("=" * 78)
    print("A fraction of NON-EMPTY certified sets, with its own n at every cell.")
    print("n = 0 means nothing was certified: no claim was made, so none failed.")
    print("`X` = the certificate FAILED at that cell and is reported as a failure.")
    print("`true` = the fraction of the box genuinely above tau. It is NOT a constant")
    print("along the ladder: gamma enters tau through tau_max multiplicatively, so a")
    print("HIGHER gamma buys a LOWER absolute tau and an EASIER containment test. Read")
    print("any containment fraction against the `true` column beside it.\n")
    table = containment_table(rows)
    failures = [c for c in table if c["below_nominal"]]
    for arm in REPORTED_ARMS:
        cells = [c for c in table if c["arm"] == arm]
        if not cells:
            continue
        print(f"--- {arm}")
        print(f"  {'gamma':>5} {'tauF':>5} {'true':>7} | " + " | ".join(
            f"a={a:<4} {'n':>3} {'frac':>6} {'v':>2}" for a in ALPHAS))
        for g in cfg["gammas"]:
            for tf in cfg["tau_fracs"]:
                parts = []
                tfrac = next((c["true_frac"] for c in cells if c["gamma"] == g
                              and c["tau_frac"] == tf), float("nan"))
                for a in ALPHAS:
                    c = next((c for c in cells if c["gamma"] == g
                              and c["tau_frac"] == tf and c["alpha"] == a), None)
                    if c is None:
                        parts.append(f"{'':<6} {'-':>3} {'-':>6} {'-':>2}")
                        continue
                    verdict = ("-" if c["below_nominal"] is None
                               else ("X" if c["below_nominal"] else "ok"))
                    frac = "nan" if c["n"] == 0 else format(c["fraction"], ".3f")
                    parts.append(f"{'':<6} {c['n']:>3} {frac:>6} {verdict:>2}")
                print(f"  {g:>5.2f} {tf:>5.2f} {tfrac:>7.5f} | " + " | ".join(parts))
        print()
    print(f"CELLS BELOW NOMINAL: {len(failures)}")
    for c in failures:
        print(f"  !! {c['arm']} gamma={c['gamma']:.2f} tau_frac={c['tau_frac']:.2f} "
              f"alpha={c['alpha']:.2f}: {c['contained']}/{c['n']} = "
              f"{c['fraction']:.4f} < {c['alpha']:.2f}  "
              f"(true_frac={c['true_frac']:.5f}, mean ce_vol={c['ce_vol']:.5f}, "
              f"{c['n_empty']} of {c['n_campaigns']} certified nothing)")
    if not failures:
        print("  none. The certificate held at every cell where it made a claim.")


def _print_contrasts(rows, cfg) -> None:
    print("\n" + "=" * 78)
    print("ARM CONTRASTS — Holm across the 24 cells, SESOI 0.02")
    print("=" * 78)
    print(f"Ranked arms: {', '.join(RANKED_ARMS)}. "
          f"plate1_only is NOT ranked -- it IS lhs (D23.1).")
    print("Wilcoxon governs yes/no; the bootstrap reports magnitude; a `!` marks a")
    print("disagreement between them, which is reported and not resolved (Q20 §2).\n")

    pairs = [("versionb", "versionb_random",
              "does the LSE criterion beat 8 RANDOM wells?"),
             ("versionb", "plate1_only",
              "does a second plate help at all? (budget-matched, 48 wells)"),
             ("versionb_predictive", "versionb",
              "does targeting the PREDICTIVE boundary beat the latent one?")]
    for key in ("iou_pred", "auc_pred", "alpha_star"):
        print(f"### {key}  [{STATUS[key]}]  (positive favours the first arm)")
        for a, b, why in pairs:
            cells, ps = [], []
            for g in cfg["gammas"]:
                for tf in cfg["tau_fracs"]:
                    pa, pb, dropped = paired(rows, a, b, key, g, tf)
                    c = contrast(pa, pb)
                    c.update({"gamma": g, "tau_frac": tf, "dropped_nan": dropped})
                    cells.append(c)
                    ps.append(c["wilcoxon_p"])
            adj = holm([1.0 if math.isnan(p) else p for p in ps])
            for c, q in zip(cells, adj):
                c["holm_p"] = q
            sig = [c for c in cells if c["holm_p"] < 0.05]
            print(f"  {a} - {b}: {why}")
            print(f"    significant after Holm at {len(sig)}/{len(cells)} cells; "
                  f"disagreements: {sum(c['disagrees'] for c in cells)}")
            for c in cells:
                if c["holm_p"] < 0.05 or c["disagrees"]:
                    print(f"      gamma={c['gamma']:.2f} tauF={c['tau_frac']:.2f} "
                          f"n={c['n']:2d} mean={c['mean']:+.4f} "
                          f"[{c['lo']:+.4f},{c['hi']:+.4f}] p={c['wilcoxon_p']:.4f} "
                          f"holm={c['holm_p']:.4f}"
                          f"{'  <SESOI' if c['within_sesoi'] else ''}"
                          f"{'  !' if c['disagrees'] else ''}"
                          f"  dropped(nan)={c['dropped_nan']}")
        print()


def _print_plate1_is_lhs(rows) -> None:
    """D23.1, measured again on this run rather than quoted."""
    if not SPREAD.exists():
        return
    lhs = [r for r in json.loads(SPREAD.read_text())["rows"] if r["arm"] == "lhs"]
    ours = [r for r in rows if r["arm"] == "plate1_only"]
    if not ours or not lhs:
        return
    ref = {(r["instance"], r["seed"], r["gamma"], r["tau_frac"]): r for r in lhs}
    worst = 0.0
    for r in ours:
        k = (r["instance"], r["seed"], r["gamma"], r["tau_frac"])
        if k in ref:
            worst = max(worst, abs(float(r["regret"]) - float(ref[k]["regret"])))
    print("\n" + "=" * 78)
    print("D23.1 — plate1_only IS lhs")
    print("=" * 78)
    print(f"  worst |delta| on regret across {len(ours)} rows: {worst:.3e}")
    print("  Both are reported. Neither is counted twice. plate1_only is not an arm in "
          "any ranking above.")


def main() -> None:
    data = json.loads(IN.read_text())
    rows, cfg = data["rows"], data["config"]
    n_keys = len({(r["instance"], r["seed"]) for r in rows})
    print(f"P2 · Version B on the gamma ladder · {len(rows)} rows · "
          f"{n_keys} (instance, seed) pairs · d={cfg['dim']} sigma={cfg['sigma']}")
    print(f"source: {IN.relative_to(ROOT)} @ {data['provenance']['git_sha'][:8]} "
          f"({data['provenance']['generated_at']})\n")

    _print_gate(data)
    _print_ladder(rows, cfg)
    _print_containment(rows, cfg)
    _print_contrasts(rows, cfg)
    _print_plate1_is_lhs(rows)


if __name__ == "__main__":
    main()
