"""E7 · the identification gap under rule P, as a COMMITTED artefact.

Registered in `docs/OPEN-QUESTIONS.md` (Erratum 32 block, `04eeebf`) **before this file
existed**. §34.3 reported this column as an in-session join; a join nobody can re-run is
not a result, so this writes it down.

**ZERO NEW CAMPAIGNS.** Every column here already exists in a committed file. This runner
builds no oracle, fits no GP and evaluates no design -- a test asserts the source contains
none of the constructors that would let it.

THE TWO JOINS, AND WHY EACH IS VALID
-------------------------------------
**σ = 0.25** · `step0-oracle-best.json.oracle_best` × `fix1-terminal-rule.json.regret_p`.
Valid because the two files describe the same campaigns: their `rule_a` / `regret_a`
columns agree to **5.55e-16** over all 300 shared keys. Checked at run time, not assumed.

**σ = 0.10** · `q57-search-vs-id.json.{doe,bo,nei}_oracle_best` ×
`versionc-gate-s010.json.regret_p`. Valid because the two files share **50 of 50**
`(instance, seed)` keys. Also checked at run time.

**`bo_` IS `qlogei` and `nei_` IS `qlognei`.** Erratum 32 exists because I did not know
that and withdrew two correct figures for having "no committed source". The mapping is a
module constant here so the mistake cannot repeat silently.

WHAT THIS FILE REFUSES TO DO
-----------------------------
* Rank `plate1_only`. It **is** `lhs` at 48 wells (Erratum 29).
* Report a spread without its arm set. **0.0395 over five arms and 0.0420 including
  `qlogei` are both correct** (Erratum 32); a spread whose arm set is not attached is a
  number that can be quoted against the wrong denominator.
* Enter `versionb` at σ = 0.25. The only Version B ceiling row is
  `versionb_plate1_ceiling` at **40 wells**, not 48, and is excluded with its reason.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
OUT = R / "e7-search-vs-id-rule-p.json"

STEP0 = R / "step0-oracle-best.json"
FIX1 = R / "fix1-terminal-rule.json"
Q57 = R / "q57-search-vs-id.json"
VC010 = R / "versionc-gate-s010.json"
#: SPADE's `oracle_best` at 48 wells. No committed file carried it -- step0 has only
#: `versionb_plate1_ceiling` at 40 -- which is the whole reason SPADE was absent from E7.
#: Gated clean at |delta| = 0 on lhs/sobol/random/plate1_only against step0.
FILL = R / "e7-oracle-best-fill.json"
FILL_ARMS = ("versionb", "versionb_random", "versionb_predictive",
             "lhs", "sobol", "random", "plate1_only")

#: Erratum 32. `bo_*` and `nei_*` are arm names in disguise.
Q57_ARM = {"doe": "doe", "bo": "qlogei", "nei": "qlognei"}

#: `plate1_only` IS `lhs` at 48 wells. Ranking both makes `lhs` a second arm (Erratum 29).
NEVER_RANK_SEPARATELY = {"plate1_only": "lhs"}

#: 40 wells, not 48. Carried as a labelled exclusion rather than dropped silently.
EXCLUDED = {"versionb_plate1_ceiling":
            "40 wells, not the shared 48 -- not comparable to the other arms"}

N_BOOT, BOOT_SEED = 4000, 0
JOIN_TOL = 1e-12


class JoinInvalid(RuntimeError):
    """The two files do not describe the same campaigns, so the join means nothing."""


def gap(rule_value: float, oracle_best: float) -> float:
    """Identification gap. Both are regrets, so the gap is how much the rule gives away."""
    return float(rule_value) - float(oracle_best)


def rankable(arms) -> list:
    return [a for a in arms if a not in NEVER_RANK_SEPARATELY and a not in EXCLUDED]


def spread(mean_gaps: dict) -> dict:
    """Max minus min, **with the arm set attached** (Erratum 32)."""
    arms = sorted(mean_gaps)
    vals = [mean_gaps[a] for a in arms]
    return {"spread": (max(vals) - min(vals)) if vals else None,
            "arms": arms, "n_arms": len(arms)}


def _rows(path: Path) -> list:
    return json.loads(path.read_text())["rows"]


def fill_table(sigma: float) -> dict:
    """`(instance, seed, arm) -> oracle_best` at 48 wells, for the arms nothing carried.

    Refuses a fill file with any gate failure: the four gated arms vouch for the
    construction that produced SPADE's column, and if they missed, SPADE's is worthless.
    """
    if not FILL.exists():
        return {}
    d = json.loads(FILL.read_text())
    if d.get("gate_failures"):
        raise JoinInvalid(
            f"{FILL.name} has {len(d['gate_failures'])} gate failures; its oracle_best "
            f"column does not reproduce step0 and cannot be joined")
    return {(r["instance"], r["seed"], r["arm"]): r["oracle_best"]
            for r in d["rows"] if r["sigma"] == sigma}


def q57_rule_a_gaps() -> dict:
    """`{(dim, sigma): {arm: mean rule-A gap}}` -- the figures Erratum 32 reinstated."""
    out = {}
    rows = _rows(Q57)
    for dim, sigma in sorted({(r["dim"], r["sigma"]) for r in rows}):
        cell = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
        out[(dim, sigma)] = {
            arm: float(np.mean([gap(r[f"{p}_rule_a"], r[f"{p}_oracle_best"])
                                for r in cell]))
            for p, arm in Q57_ARM.items()}
    return out


def _paired_stats(a: list, p: list) -> dict:
    """Wilcoxon governs yes/no; the bootstrap reports magnitude (Q20 §2)."""
    a, p = np.asarray(a, float), np.asarray(p, float)
    d = p - a
    rng = np.random.default_rng(BOOT_SEED)
    boot = np.array([rng.choice(d, d.size, replace=True).mean() for _ in range(N_BOOT)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    try:
        w = float(wilcoxon(p, a).pvalue)
    except ValueError:                                   # all-zero differences
        w = 1.0
    return {"n": int(d.size), "gap_rule_a": float(a.mean()), "gap_rule_p": float(p.mean()),
            "shift": float(d.mean()), "wilcoxon_p": w,
            "boot_ci95": [float(lo), float(hi)],
            "ci_excludes_zero": bool(lo > 0 or hi < 0)}


def cell_sigma_025() -> dict:
    """step0 (`oracle_best`) × fix1 (`regret_p`), plus `qlogei` via q57."""
    s0 = {(r["instance"], r["seed"], r["arm"]): r for r in _rows(STEP0)}
    f1 = {(r["instance"], r["seed"], r["arm"]): r for r in _rows(FIX1)}

    shared = sorted(set(s0) & set(f1))
    worst = max(abs(s0[k]["rule_a"] - f1[k]["regret_a"]) for k in shared)
    if worst > JOIN_TOL:
        raise JoinInvalid(f"step0.rule_a vs fix1.regret_a differ by {worst:.3e} over "
                          f"{len(shared)} keys; these are not the same campaigns")

    per_arm, arms = {}, sorted({k[2] for k in shared})
    for arm in arms:
        ks = [k for k in shared if k[2] == arm]
        per_arm[arm] = _paired_stats([gap(s0[k]["rule_a"], s0[k]["oracle_best"]) for k in ks],
                                     [gap(f1[k]["regret_p"], s0[k]["oracle_best"]) for k in ks])

    # qlogei: oracle_best from q57, regret_p from fix1. A THIRD join, checked separately.
    q = {(r["instance"], r["seed"]): r for r in _rows(Q57)
         if r["dim"] == 6 and r["sigma"] == 0.25}
    fq = {(r["instance"], r["seed"]): r for r in _rows(FIX1) if r["arm"] == "qlogei"}
    kq = sorted(set(q) & set(fq))
    qlogei_note = None
    if len(kq) == len(fq) == 50:
        wq = max(abs(q[k]["bo_rule_a"] - fq[k]["regret_a"]) for k in kq)
        if wq <= JOIN_TOL:
            per_arm["qlogei"] = _paired_stats(
                [gap(q[k]["bo_rule_a"], q[k]["bo_oracle_best"]) for k in kq],
                [gap(fq[k]["regret_p"], q[k]["bo_oracle_best"]) for k in kq])
        else:
            qlogei_note = (f"q57.bo_rule_a vs fix1.qlogei.regret_a differ by {wq:.3e}; "
                           f"qlogei EXCLUDED rather than joined across drifted files")
    else:
        qlogei_note = f"key overlap {len(kq)} of 50; qlogei EXCLUDED"

    # SPADE. oracle_best from the fill, regret_p from fix1. The reason E7 exists at all.
    fill = fill_table(0.25)
    f1_by = {}
    for r in _rows(FIX1):
        f1_by.setdefault(r["arm"], {})[(r["instance"], r["seed"])] = r
    for arm in FILL_ARMS:
        if arm in per_arm or arm not in f1_by:
            continue
        ks = [k for k in sorted(f1_by[arm]) if (k[0], k[1], arm) in fill]
        if len(ks) != len(f1_by[arm]):
            continue
        per_arm[arm] = _paired_stats(
            [gap(f1_by[arm][k]["regret_a"], fill[(k[0], k[1], arm)]) for k in ks],
            [gap(f1_by[arm][k]["regret_p"], fill[(k[0], k[1], arm)]) for k in ks])

    rk = rankable(per_arm)
    return {"sigma": 0.25, "n_keys": len(shared) // max(len(arms), 1),
            "join": {"step0_x_fix1_worst_abs_delta": worst, "n_shared_keys": len(shared)},
            "per_arm": per_arm, "excluded": EXCLUDED,
            "never_rank_separately": NEVER_RANK_SEPARATELY, "qlogei_note": qlogei_note,
            "spread_rule_a": {
                "including_doe": spread({a: per_arm[a]["gap_rule_a"] for a in rk}),
                "excluding_doe": spread({a: per_arm[a]["gap_rule_a"]
                                         for a in rk if a != "doe"})},
            "spread_rule_p": {
                "including_doe": spread({a: per_arm[a]["gap_rule_p"] for a in rk}),
                "excluding_doe": spread({a: per_arm[a]["gap_rule_p"]
                                         for a in rk if a != "doe"})}}


def cell_sigma_010() -> dict:
    """q57 (`oracle_best`) × versionc-gate-s010 (`regret_p`). Erratum 32's other half."""
    q = {(r["instance"], r["seed"]): r for r in _rows(Q57)
         if r["dim"] == 6 and r["sigma"] == 0.1}
    v = {}
    for r in _rows(VC010):
        v.setdefault((r["instance"], r["seed"]), {})[r["arm"]] = r
    if set(q) != set(v):
        raise JoinInvalid(f"q57 sigma=0.10 has {len(q)} keys, versionc-gate has {len(v)}; "
                          f"the join is only valid across identical key sets")
    keys = sorted(q)
    per_arm = {}
    for prefix, arm in Q57_ARM.items():
        ks = [k for k in keys if arm in v[k]]
        if len(ks) != len(keys):
            continue
        per_arm[arm] = _paired_stats(
            [gap(q[k][f"{prefix}_rule_a"], q[k][f"{prefix}_oracle_best"]) for k in ks],
            [gap(v[k][arm]["regret_p"], q[k][f"{prefix}_oracle_best"]) for k in ks])
    fill = fill_table(0.10)
    for arm in FILL_ARMS:
        if arm in per_arm:
            continue
        ks = [k for k in keys if arm in v[k] and (k[0], k[1], arm) in fill]
        if len(ks) != len(keys):
            continue
        per_arm[arm] = _paired_stats(
            [gap(v[k][arm]["regret_a"], fill[(k[0], k[1], arm)]) for k in ks],
            [gap(v[k][arm]["regret_p"], fill[(k[0], k[1], arm)]) for k in ks])

    rk = rankable(per_arm)
    return {"sigma": 0.10, "n_keys": len(keys),
            "join": {"n_shared_keys": len(keys), "key_sets_identical": True},
            "per_arm": per_arm,
            "coverage_limit": ("doe/qlogei/qlognei from q57; SPADE and the spread arms "
                               "from e7-oracle-best-fill.json at 48 wells, gated clean. "
                               "qlogei-add / qlogei-addonly are not filled."),
            "spread_rule_a": {"including_doe": spread(
                {a: per_arm[a]["gap_rule_a"] for a in rk})},
            "spread_rule_p": {"including_doe": spread(
                {a: per_arm[a]["gap_rule_p"] for a in rk})}}


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import scipy
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sources": {p.name: _git("log", "-1", "--format=%H", "--", f"results/{p.name}")
                        for p in (STEP0, FIX1, Q57, VC010)}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    final = Path(args.out) if args.out else OUT

    print("E7 · rule-P identification gap · ZERO NEW CAMPAIGNS")
    c25, c10 = cell_sigma_025(), cell_sigma_010()
    print(f"  sigma=0.25 join checked: worst |delta| = "
          f"{c25['join']['step0_x_fix1_worst_abs_delta']:.3e} over "
          f"{c25['join']['n_shared_keys']} keys")
    print(f"  sigma=0.10 join checked: {c10['join']['n_shared_keys']} keys, identical sets\n")

    for cell in (c25, c10):
        print(f"--- sigma = {cell['sigma']} ---")
        print(f"  {'arm':<14}{'gap ruleA':>11}{'gap ruleP':>11}{'shift':>10}"
              f"{'wilcoxon':>11}   boot 95% CI")
        for arm in sorted(cell["per_arm"], key=lambda a: cell["per_arm"][a]["gap_rule_a"]):
            s = cell["per_arm"][arm]
            lo, hi = s["boot_ci95"]
            print(f"  {arm:<14}{s['gap_rule_a']:>+11.4f}{s['gap_rule_p']:>+11.4f}"
                  f"{s['shift']:>+10.4f}{s['wilcoxon_p']:>11.2e}   "
                  f"[{lo:+.4f}, {hi:+.4f}]")
        for name in ("spread_rule_a", "spread_rule_p"):
            for which, sp in cell[name].items():
                print(f"    {name}.{which}: {sp['spread']:.4f}  "
                      f"over {sp['n_arms']} arms {sp['arms']}")
        print()

    final.write_text(json.dumps(
        {"status": "COMPLETE", "provenance": _provenance(sys.argv),
         "config": {"n_boot": N_BOOT, "boot_seed": BOOT_SEED, "join_tol": JOIN_TOL,
                    "q57_arm_map": Q57_ARM, "zero_new_campaigns": True},
         "cells": [c25, c10]}, indent=1))
    print(f"wrote {final.name}")


if __name__ == "__main__":
    main()
