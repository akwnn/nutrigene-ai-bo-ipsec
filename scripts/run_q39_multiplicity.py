"""Q39 / T2.3 — Holm correction over every comparison outside the registered primaries.

    python scripts/run_q39_multiplicity.py     # log at results/q39-multiplicity.log

`e2.yaml` registers `report_all_comparisons: true`, which is the right call — it removes
the selection problem outright rather than managing it. But reporting every comparison
and then reading each *p* against 0.05 reintroduces the problem at the other end. This
applies the correction the config never specified.

WHAT COUNTS AS PRIMARY
----------------------
Only contrasts registered BEFORE their run, in a committed file, are exempt:

  E2   `qlogei` vs `doe`, d=6 sigma=0.25   -- configs/experiment/e2.yaml `primary_domain`
  Q34  cell 5 - cell 3, d=6 sigma=0.25     -- OPEN-QUESTIONS Q34, committed in a1420d4

`coprimary_methods` (`best_non_bo`) is NOT exempt: `e2.yaml` itself labels it a
post-hoc-selected comparator, so it is a max-statistic over ~5 arms and belongs in the
corrected family by the same logic that puts everything else there.

Everything else -- every other cell, every other arm, every secondary contrast in
Q34/Q35/Q36 -- is corrected together with Holm, which controls the family-wise error
rate without assuming independence. These tests are strongly dependent (same campaigns,
same instances, overlapping arms), and Holm is valid under arbitrary dependence whereas
Benjamini-Hochberg is not.

REPORTED AS: effect size and interval FIRST, p second, adjusted p third. A contrast
whose verdict changes under correction is flagged, because that is the only thing the
correction can actually tell you.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import wilcoxon                    # noqa: E402

from boec.diagnostics import instance_bootstrap     # noqa: E402

RESULTS = ROOT / "results"
ALPHA = 0.05
RULE = "=" * 112

#: (source, cell, label) of contrasts registered before their run. Nothing else.
REGISTERED_PRIMARY = {
    ("E2", "d=6 s=0.25", "doe - qlogei"),
    ("Q34", "d=6 s=0.25", "cell5 - cell3"),
}


def _paired(a: np.ndarray, b: np.ndarray) -> dict:
    d = a - b
    m, lo, hi = instance_bootstrap(d, n_boot=2000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(effect=float(m), lo=float(lo), hi=float(hi), p=p, n=int(len(d)))


def _by_instance(rows, key, cell_filter, value_key):
    sub = [r for r in rows if cell_filter(r)]
    ids = sorted({r[key] for r in sub})
    out = []
    for i in ids:
        vals = [r[value_key] for r in sub if r[key] == i]
        if any(v is None for v in vals):
            return None
        out.append(np.mean(vals))
    return np.array(out, dtype=float)


def collect() -> list[dict]:
    tests: list[dict] = []

    # ---- E2: every arm against qlogei, every cell ---------------------------
    grid = json.loads((RESULTS / "e2-grid.json").read_text())
    for dim in (6, 8):
        for sigma in (0.25, 0.1):
            cell = f"d={dim} s={sigma}"
            sub = [r for r in grid if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
            insts = sorted({r["instance"] for r in sub})
            arms = sorted({r["arm"] for r in sub})
            if "qlogei" not in arms:
                continue
            base = np.array([np.mean([r["regret"] for r in sub
                                      if r["arm"] == "qlogei" and r["instance"] == i])
                             for i in insts])
            for arm in arms:
                if arm == "qlogei":
                    continue
                v = np.array([np.mean([r["regret"] for r in sub
                                       if r["arm"] == arm and r["instance"] == i])
                              for i in insts])
                tests.append(dict(source="E2", cell=cell, label=f"{arm} - qlogei",
                                  **_paired(v, base)))

    # ---- Q34: the factorial contrasts ---------------------------------------
    p34 = RESULTS / "q34-factorial.json"
    if p34.exists():
        rows = json.loads(p34.read_text())
        pairs = [("cell5_doe_gp", "cell3_doe_poly", "cell5 - cell3"),
                 ("cell4_bo_gp", "cell6_bo_poly", "cell4 - cell6"),
                 ("cell4_bo_gp", "cell5_doe_gp", "cell4 - cell5"),
                 ("cell3_doe_poly", "cell6_bo_poly", "cell3 - cell6")]
        for dim in (6, 8):
            for sigma in (0.25, 0.1):
                f = lambda r: r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12  # noqa: E731,B023
                for a, b, label in pairs:
                    va = _by_instance(rows, "instance", f, a)
                    vb = _by_instance(rows, "instance", f, b)
                    if va is None or vb is None or va.size == 0:
                        continue
                    tests.append(dict(source="Q34", cell=f"d={dim} s={sigma}",
                                      label=label, **_paired(va, vb)))

    # ---- Q35: the three DoE scorings ----------------------------------------
    p35 = RESULTS / "q35-constrained-rsm.json"
    if p35.exists():
        rows = json.loads(p35.read_text())
        pairs = [("unconstrained", "constrained", "unconstrained - constrained"),
                 ("constrained", "best_observed", "constrained - best observed"),
                 ("unconstrained", "best_observed", "unconstrained - best observed")]
        for dim in (6, 8):
            for sigma in (0.25, 0.1):
                f = lambda r: r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12  # noqa: E731,B023
                for a, b, label in pairs:
                    va, vb = (_by_instance(rows, "instance", f, a),
                              _by_instance(rows, "instance", f, b))
                    if va is None or vb is None or va.size == 0:
                        continue
                    tests.append(dict(source="Q35", cell=f"d={dim} s={sigma}",
                                      label=label, **_paired(va, vb)))

    # ---- Q36: generality ----------------------------------------------------
    p36 = RESULTS / "q36-generality.json"
    if p36.exists():
        rows = json.loads(p36.read_text())["rows"]
        pairs = [("doe_a", "bo_a", "rule A: doe - bo"),
                 ("doe_c_unconstrained", "bo_c", "rule C unconstr: doe - bo"),
                 ("doe_c_constrained", "bo_c", "rule C constr: doe - bo")]
        for fn in sorted({r["function"] for r in rows}):
            sub = [r for r in rows if r["function"] == fn]
            for a, b, label in pairs:
                va = np.array([r[a] for r in sub], dtype=float)
                vb = np.array([r[b] for r in sub], dtype=float)
                tests.append(dict(source="Q36", cell=fn, label=label,
                                  **_paired(va, vb)))
    return tests


def _ci(t: dict) -> str:
    return f"[{t['lo']:+.4f},{t['hi']:+.4f}]"


def holm(ps: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, monotonised. Valid under arbitrary dependence."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * ps[i])
        running = max(running, val)          # enforce monotonicity
        adj[i] = running
    return adj


def main() -> None:
    tests = collect()
    prim = [t for t in tests if (t["source"], t["cell"], t["label"]) in REGISTERED_PRIMARY]
    sec = [t for t in tests if (t["source"], t["cell"], t["label"]) not in REGISTERED_PRIMARY]
    adj = holm([t["p"] for t in sec])
    for t, a in zip(sec, adj):
        t["p_holm"] = a

    print(f"{RULE}\nQ39 · multiplicity — Holm over every comparison outside the "
          f"registered primaries\n{RULE}")
    print(f"  {len(prim)} registered primary contrast(s), exempt.")
    print(f"  {len(sec)} secondary contrasts, Holm-corrected together at alpha={ALPHA}.\n")

    print("REGISTERED PRIMARIES — not corrected, because they were fixed before the run")
    print(f"{'source':>6}{'cell':>13}{'contrast':>32}{'effect':>10}"
          f"{'95% CI':>22}{'p':>10}")
    for t in prim:
        print(f"{t['source']:>6}{t['cell']:>13}{t['label']:>32}{t['effect']:>+10.4f}"
              f"{_ci(t):>22}{t['p']:>10.4f}")

    print(f"\nSECONDARY — effect and interval first, then raw p, then Holm-adjusted p")
    print(f"{'source':>6}{'cell':>13}{'contrast':>32}{'effect':>10}"
          f"{'95% CI':>22}{'raw p':>9}{'Holm p':>9}  verdict")
    flipped = []
    for t in sorted(sec, key=lambda x: x["p"]):
        raw_sig = t["p"] < ALPHA
        adj_sig = t["p_holm"] < ALPHA
        ci_excl = (t["lo"] > 0) or (t["hi"] < 0)
        mark = ""
        if raw_sig and not adj_sig:
            mark = "  <-- LOST under correction"
            flipped.append(t)
        print(f"{t['source']:>6}{t['cell']:>13}{t['label']:>32}{t['effect']:>+10.4f}"
              f"{_ci(t):>22}{t['p']:>9.4f}{t['p_holm']:>9.4f}  "
              f"{'sig' if adj_sig else 'ns':<4}"
              f"{'CI excl 0' if ci_excl else 'CI incl 0':<10}{mark}")

    print(f"\n{RULE}\nWHAT THE CORRECTION ACTUALLY CHANGED\n{RULE}")
    if flipped:
        print(f"  {len(flipped)} contrast(s) significant at raw alpha lose it under Holm:")
        for t in flipped:
            print(f"    {t['source']} {t['cell']} {t['label']}: "
                  f"p={t['p']:.4f} -> {t['p_holm']:.4f}")
    else:
        print("  NOTHING. Every contrast significant at raw alpha survives Holm, and\n"
              "  every non-significant one stays non-significant. The effects in this\n"
              "  project are large relative to their intervals, so multiplicity was never\n"
              "  what was holding the conclusions up -- which is worth stating precisely\n"
              "  BECAUSE it was not checked before.")
    n_ci_disagree = sum(1 for t in sec
                        if ((t["lo"] > 0) or (t["hi"] < 0)) != (t["p_holm"] < ALPHA))
    print(f"\n  the 95% CI and the Holm-adjusted Wilcoxon disagree on {n_ci_disagree} of "
          f"{len(sec)} secondary contrasts.")
    print("""
  READ THAT DISAGREEMENT CAREFULLY -- IT IS NOT EVIDENCE FOR THE INTERVAL.
  The intervals above are per-contrast 95% intervals. They are NOT simultaneous, so
  across a family of this size several are expected to exclude zero by chance. Setting
  an uncorrected interval against a corrected p and preferring the interval would undo
  the correction by the back door, which is the opposite of what T2.3 asks for.

  The coherent split, and the one used from here on:
    MAGNITUDE   the effect and its per-contrast interval, reported for every contrast,
                descriptively. This is what "intervals are primary" means -- an effect
                size and its precision are what a reader needs, not a yes/no.
    VERDICT     inside the registered primaries, the per-contrast interval and p.
                Outside them, the HOLM-ADJUSTED p. A secondary contrast whose interval
                excludes zero but whose adjusted p does not clear alpha is reported as
                a suggestive effect of the stated size, never as a finding.

  Separately, and pushing the same way: a signed-rank test on a skewed paired
  difference is anti-conservative -- measured at 8.9% against a nominal 5% in defect 9 --
  so the raw p-values here are, if anything, already too small before correction.""")

    (RESULTS / "q39-multiplicity.json").write_text(
        json.dumps(dict(primary=prim, secondary=sec), indent=1))
    print(f"\n  written to results/q39-multiplicity.json")


if __name__ == "__main__":
    main()
