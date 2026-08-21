"""P7 -- Murphy calibration-refinement decomposition at the primary cell.

Registered in `docs/OPEN-QUESTIONS.md` at commit 5c44e6a, under Amendment A5, before
this file existed. Amendment A5's argument is that the project has only ever reported
the SUM: `Brier = calibration - refinement + uncertainty`, and refinement is the term
that actually rewards a probability map for separating the superlevel set from its
complement. This re-scores the one populated design-space cell and asks whether the two
rank the arms differently.

REGISTERED DECISION RULE, WINNER NOT PRE-WRITTEN
------------------------------------------------
Ranking by refinement differs from ranking by Brier at any cell -> the decomposition has
found something, and that is the A5 result. Identical at every cell -> A5 is a NULL and
is written up as one.

The verdict is taken on the PREDICTIVE map. Peterson's `D_gamma` is the primary object
throughout this project (`boec.designspace` module docstring); the latent map is scored
alongside and reported, and disagreement between them is a reported result, not a
tie-break.

WHY THE CAMPAIGNS ARE REGENERATED
---------------------------------
No file in `results/` stores a probability map, so the maps must be recomputed, which
means the campaigns must be regenerated (`boec.replay`). Two independent gates against
COMMITTED columns hold that regeneration honest (D12 -- never gate a regeneration
against a regeneration of itself):

  1. REGRET, against `results/e2-grid.json`. The registered gate. Tolerance is read
     from `results/k1-replay-gate.json`, which measured it; it is never a constant
     chosen here, and it is never raised.
  2. BRIER, against `k6-designspace.json` / `k6-designspace-spread.json`
     `brier_pred` / `brier_latent`. Stronger than the regret gate for this question:
     regret agreeing proves the campaign reproduced, but `brier_raw` agreeing proves
     the same 20,000-point MAP was rebuilt, which is the object being decomposed.

ARMS
----
The six arms with a committed regret column at this cell that `replay.regenerate`
supports. `coord` has a committed column but no `regenerate` path (it is P4's task);
`qlogei-add` / `qlogei-addonly` have a `regenerate` path but no committed column at this
cell (CANNOT GATE, COVERAGE-MATRIX 3.6 -- P1 is building that comparator). Running an
ungateable arm here would put an ungated number into a ranking, so neither is included.

THE PERFORMANCE TRAP
--------------------
`model.posterior(X)` builds the JOINT covariance over all of X: 0.06 s at N=2,000 and
100.6 s at N=20,000. `designspace.gp_adapter` chunks at POSTERIOR_CHUNK = 2048 and is
the only path used here.
"""

from __future__ import annotations

import argparse
import gc
import itertools
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

# ERRATUM 2: this project's fidelity regime is EXACT equality, and BLAS thread count
# changes the order of floating-point reductions. Nothing in the repository has ever
# recorded the thread count a |delta| = 0 gate was measured under. It is capped here,
# recorded in `provenance`, and the map gate below -- which compares against k6 columns
# produced at the torch DEFAULT thread count -- is what turns "expected to survive" into
# a measurement.
torch.set_num_threads(1)

from boec.calibration import (N_BINS, average_precision, error_volumes,  # noqa: E402
                              murphy_decomposition)
from boec.designspace import (brier_and_auc, false_inclusion_rate, gp_adapter,  # noqa: E402
                              iou, predictive_probability_map, probability_map, tau_max)
from boec.norms import sobol_grid
from boec.replay import committed_rows, instance_by_id, regenerate, unit_bounds
from boec.surrogate import build_gp
from boec.torch_oracle import BiphasicOracle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p7-murphy.json"
#: In-progress checkpoints go HERE, never to OUT. `.gitignore:20` ignores `results/*`
#: while line 211 NEGATES `results/p7-murphy.json` -- so the final path is stageable and
#: an 8%-complete file sitting there would read as the finished Murphy result: full
#: provenance, a gate block, and nothing to distinguish it. Two of two long runners hit
#: this tonight. OUT is written ONCE, whole, at the end; this path carries everything
#: before that and is unstageable by construction.
CKPT = ROOT / "results/p7-murphy.partial.json"
GATE = ROOT / "results/k1-replay-gate.json"
#: Committed map columns. `brier_raw` must reproduce these, or the map is not the map.
MAP_GATE = (ROOT / "results/k6-designspace.json",
            ROOT / "results/k6-designspace-spread.json")

#: The primary cell. Not parameters -- the only (family, d, sigma_rel) cell that carries
#: any design-space metric at all (COVERAGE-MATRIX 2.1).
DIM = 6
SIGMA = 0.25
ARMS = ("doe", "qlogei", "qlognei", "lhs", "sobol", "random")
#: K6's grid, unchanged, so every row sits beside a committed Brier.
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
GRID_N = 20_000
GRID_SEED = 0

#: Registered: the identity must hold to this, or the row is NOT written.
IDENTITY_BAR = 1e-10
#: Amendment E statistics, restated in the P7 registration block.
N_BOOT = 4000
BOOT_SEED = 0


def _git(*a: str) -> str:
    try:
        return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _is_tracked(path: Path) -> bool:
    """Is this file committed to git? The guard on every write-back path.

    `_git` swallows failures and returns "unknown", which is TRUTHY, so it must never be
    used for a boolean question -- an untracked file would read as tracked and a tracked
    one as tracked too. This asks the exit status instead.
    """
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
                          capture_output=True).returncode == 0


def _provenance(argv: list[str]) -> dict:
    import botorch
    import gpytorch
    import scipy
    return dict(
        git_sha=_git("rev-parse", "HEAD"), git_dirty=bool(_git("status", "--porcelain")),
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=argv,
        python=platform.python_version(), torch=torch.__version__,
        torch_threads=torch.get_num_threads(),
        thread_env={k: os.environ.get(k) for k in
                    ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
        botorch=botorch.__version__, gpytorch=gpytorch.__version__,
        numpy=np.__version__, scipy=scipy.__version__,
        config=dict(family="hill", dim=DIM, sigma_rel=SIGMA, arms=list(ARMS),
                    gammas=list(GAMMAS), tau_fracs=list(TAU_FRACS), grid_n=GRID_N,
                    grid_seed=GRID_SEED, n_bins=N_BINS, identity_bar=IDENTITY_BAR,
                    n_boot=N_BOOT, boot_seed=BOOT_SEED,
                    primary_map="pred", verdict_source="pred"),
    )



def result_document(status: str, keys_present: int, keys_expected: int,
                    argv: list[str], gate_fail: list, map_fail: list, worst_map: dict,
                    n_map_checked: int, identity_fail: list, worst_identity: float,
                    rows: list) -> dict:
    """The result document. `status` is FIRST because it is what a reader must see.

    **Deliberately not named `payload`.** It was, and `main` also bound a local named
    `payload` in its `--summarise` branch -- which makes `payload` local to the WHOLE
    function under Python's scoping rules, so the checkpoint write hundreds of lines
    earlier raised `UnboundLocalError` and killed a live run at 5 of 50 keys. The name
    here is one no local in `main` uses, and a test asserts that stays true.

    A partial file that carries a full provenance block and a gate section is
    indistinguishable from a finished one unless it says so itself, and no downstream
    script should have to count keys to find out.
    """
    return {
        "status": status,
        "keys_present": keys_present, "keys_expected": keys_expected,
        "provenance": _provenance(argv),
        "gate_failures": gate_fail,
        "map_gate": {"target": [str(q.relative_to(ROOT)) for q in MAP_GATE],
                     "columns": list(GATED_COLUMNS), "rows_checked": n_map_checked,
                     "worst_abs_delta": worst_map, "failures": map_fail},
        "identity": {"bar": IDENTITY_BAR, "max_residual": worst_identity,
                     "failures": identity_fail},
        "rows": rows,
    }


def _gate_tol(arm: str) -> float:
    """The tolerance K1-gate MEASURED. Never a constant chosen here, never raised."""
    if not GATE.exists():
        return 0.0
    pol = json.loads(GATE.read_text()).get("policy", {})
    return float(pol.get(arm, {}).get("worst_abs_delta", 0.0))


#: Every K6 column this re-score independently recomputes. Gating all of them is a far
#: stronger statement than gating regret alone: regret agreeing proves the CAMPAIGN
#: reproduced, these agreeing prove the same 20,000-point MAP was rebuilt, which is the
#: object being decomposed. Under ERRATUM 2 it is also the thread-count evidence -- these
#: columns were produced at the torch default and are re-derived here at one thread.
GATED_COLUMNS = ("true_frac_above_tau", "brier_pred", "brier_latent", "auc_pred",
                 "auc_latent", "vol_pred", "vol_latent", "iou_pred", "iou_latent",
                 "fi_pred", "fi_latent")


def _committed_maps() -> dict:
    """`(instance, seed, arm, gamma, tau_frac) -> {column: value}` from K6."""
    out = {}
    for path in MAP_GATE:
        if not path.exists():
            continue
        for r in json.loads(path.read_text())["rows"]:
            out[(r["instance"], r["seed"], r["arm"], r["gamma"], r["tau_frac"])] = {
                c: r[c] for c in GATED_COLUMNS}
    return out


#: Committed K6 column -> the key this runner stores it under.
MINE_FOR = {"true_frac_above_tau": "true_frac_above_tau",
            "brier_pred": "pred_brier_raw", "brier_latent": "latent_brier_raw",
            "auc_pred": "pred_auc", "auc_latent": "latent_auc",
            "vol_pred": "pred_vol", "vol_latent": "latent_vol",
            "iou_pred": "pred_iou", "iou_latent": "latent_iou",
            "fi_pred": "pred_fi", "fi_latent": "latent_fi"}


def _same(a: float, b: float) -> bool:
    """Exact equality, with nan == nan. An empty region legitimately gives nan on both
    sides, and `nan != nan` would report that agreement as a gate failure."""
    if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
        return True
    return a == b


def score_campaign(rec, orc, grid, truth) -> tuple[list[dict], list[dict], float]:
    """Every (gamma, tau_frac) decomposition for one regenerated campaign.

    Returns `(rows, identity_failures, worst_residual)`. A row whose identity residual
    exceeds the registered bar is NOT written -- that is the registration's instruction,
    not a judgement call made here.
    """
    model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(rec.dim))
    # CHUNKED. See the module docstring: 100.6 s unchunked at this grid size.
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    class _M:
        def posterior_mean_and_sd(self, X):
            return mean, sd

    m = _M()
    # A lab does not know f, so the predictive SD is a PLUG-IN from the posterior mean.
    # Identical expression to run_k6_designspace.score_campaign, so the maps coincide.
    sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()

    rows, failures, worst = [], [], 0.0
    base = {"instance": rec.instance, "dim": rec.dim, "sigma": rec.sigma,
            "seed": rec.seed, "arm": rec.arm, "regret": rec.regret}

    for gamma in GAMMAS:
        tmax = tau_max(gamma, orc.sigma_rel)
        for tf in TAU_FRACS:
            tau = round(tf * tmax, 10)
            maps = {"pred": predictive_probability_map(m, grid, tau, sigma_pred),
                    "latent": probability_map(m, grid, tau)}
            prevalence = float((truth >= tau).double().mean())
            # AUPRC's no-skill baseline is the prevalence of the class being scored, and
            # F2b flags it primary where the MINORITY class is rarer than 1%. At high
            # gamma the minority is the NEGATIVE class -- at gamma=0.99, tau_frac=0.60
            # about 16 grid points of 20,000 are negative -- so the standard
            # positive-class AP is trivially near 1 there and says nothing. The minority
            # AP is computed by scoring the complement, and both travel with the row.
            minority = min(prevalence, 1.0 - prevalence)
            row = {**base, "gamma": gamma, "tau_frac": tf, "tau": tau, "tau_max": tmax,
                   "true_frac_above_tau": prevalence,
                   "minority_prevalence": minority,
                   "minority_class": 1 if prevalence <= 0.5 else 0,
                   "auprc_is_primary": bool(minority < 0.01)}
            ok = True
            for name, p in maps.items():
                d = murphy_decomposition(p, truth, tau, n_bins=N_BINS)
                resid = abs(d["calibration"] - d["refinement"] + d["uncertainty"]
                            - d["brier"])
                worst = max(worst, resid)
                if resid > IDENTITY_BAR:
                    ok = False
                    failures.append({**base, "gamma": gamma, "tau_frac": tf,
                                     "map": name, "residual": resid})
                    continue
                row[f"{name}_brier"] = d["brier"]
                row[f"{name}_calibration"] = d["calibration"]
                row[f"{name}_refinement"] = d["refinement"]
                row[f"{name}_uncertainty"] = d["uncertainty"]
                row[f"{name}_bin_counts"] = d["bin_counts"]
                row[f"{name}_brier_raw"] = d["brier_raw"]
                row[f"{name}_within_bin"] = d["within_bin"]
                row[f"{name}_identity_residual"] = resid
                row[f"{name}_degenerate"] = d["degenerate"]

                # --- F2b: AUPRC beside AUC, with the baseline both are read against ---
                _, auc_v = brier_and_auc(p, truth, tau)
                row[f"{name}_auc"] = auc_v
                row[f"{name}_auprc"] = average_precision(p, truth, tau)
                row[f"{name}_auprc_minority"] = (
                    row[f"{name}_auprc"] if prevalence <= 0.5
                    # Score the complement explicitly. `-truth >= -tau` would put a grid
                    # point with truth exactly tau in BOTH classes.
                    else average_precision(1.0 - p, (truth < tau).double(), 0.5))
                row[f"{name}_auprc_baseline"] = minority

                # --- F2a: the region, and its two error volumes ---
                region = p >= gamma
                vol = float(region.double().mean())
                fi = false_inclusion_rate(region, truth, tau)
                ev = error_volumes(vol, fi, prevalence)
                row[f"{name}_vol"] = vol
                row[f"{name}_empty"] = int(region.sum()) == 0
                row[f"{name}_fi"] = fi
                row[f"{name}_iou"] = iou(region, truth, tau)
                for k, v in ev.items():
                    row[f"{name}_{k}"] = v
            if ok:
                rows.append(row)
    del model, mean, sd
    gc.collect()
    return rows, failures, worst


# --- the registered decision rule -------------------------------------------------

def _order(arms: list[str], values: dict, higher_is_better: bool) -> list[str]:
    """Arms best-first. Ties broken by name so the comparison is deterministic."""
    return sorted(arms, key=lambda a: (-values[a] if higher_is_better else values[a], a))


def dual_paired_stats(a: np.ndarray, b: np.ndarray, keys: list) -> dict:
    """**Amendment F1**: every contrast at BOTH units, and n=25 governs.

    * ``n50`` -- unit ``(instance, seed)``, as K6 reported.
    * ``n25`` -- unit ``instance``, **seeds averaged first**, which is what the earlier
      paper committed to. Two seeds on one landscape share the landscape, so treating
      them as independent inflates the effective sample size and narrows every CI by
      roughly sqrt(2).

    The two means are identical whenever every instance carries the same number of
    seeds; only the intervals and the p-values move. That is asserted, not assumed --
    a differing mean would mean the design is unbalanced and the n=25 column is not the
    same contrast.
    """
    diff = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    by_instance: dict = {}
    for k, d in zip(keys, diff):
        by_instance.setdefault(k[0], []).append(d)
    inst_diff = np.array([float(np.mean(v)) for v in by_instance.values()])
    out = {"n50": _paired_stats(diff), "n25": _paired_stats(inst_diff)}
    out["means_agree"] = bool(abs(out["n50"]["mean_diff"]
                                  - out["n25"]["mean_diff"]) < 1e-12)
    out["seeds_per_instance"] = sorted({len(v) for v in by_instance.values()})
    return out


def _paired_stats(diff: np.ndarray) -> dict:
    """Amendment E: 4,000-resample percentile bootstrap AND a two-sided Wilcoxon.

    Wilcoxon governs yes/no, the bootstrap reports magnitude, and per Q20 2 a
    disagreement between them is REPORTED, not resolved.
    """
    from scipy.stats import wilcoxon
    rng = np.random.default_rng(BOOT_SEED)
    boot = rng.choice(diff, size=(N_BOOT, diff.size), replace=True).mean(axis=1)
    try:
        p = float(wilcoxon(diff, zero_method="wilcox", alternative="two-sided").pvalue)
    except ValueError:  # all differences zero
        p = 1.0
    return {"mean_diff": float(diff.mean()),
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "wilcoxon_p": p, "n": int(diff.size)}


def _holm(pvals: list[float]) -> list[float]:
    """Holm across the cells, as registered. Returns adjusted p in input order."""
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return [float(x) for x in adj]


def summarise(rows: list[dict]) -> dict:
    """Refinement ranking vs Brier ranking, per cell, for both maps.

    Campaigns whose truth is single-class at this tau are DROPPED before either mean is
    taken. Refinement is identically 0 there, for every arm alike, so keeping them would
    manufacture a ranking difference out of a degeneracy. The drop is arm-symmetric --
    the truth does not depend on the arm -- and both rankings see the same campaigns.
    """
    arms = sorted({r["arm"] for r in rows})
    cells, tests = [], []

    for gamma, tf in itertools.product(GAMMAS, TAU_FRACS):
        at = [r for r in rows if r["gamma"] == gamma and r["tau_frac"] == tf]
        if not at:
            continue
        # A campaign is keyed by (instance, seed); pairing is across arms at that key.
        degenerate_keys = {(r["instance"], r["seed"]) for r in at
                           if "single_class" in r["pred_degenerate"]}
        keys = sorted({(r["instance"], r["seed"]) for r in at} - degenerate_keys)
        cell = {"gamma": gamma, "tau_frac": tf, "n_used": len(keys),
                "n_single_class_dropped": len(degenerate_keys),
                "mean_prevalence": float(np.mean([r["true_frac_above_tau"] for r in at]))}
        if not keys:
            cell["verdict"] = "NO USABLE CAMPAIGN — every truth single-class at this tau"
            cells.append(cell)
            continue

        by = {(r["arm"], r["instance"], r["seed"]): r for r in at}
        present = [a for a in arms if all((a, *k) in by for k in keys)]
        cell["arms"] = present

        for mp in ("pred", "latent"):
            vec = {q: {a: np.array([(np.nan if by[(a, *k)][f"{mp}_{q}"] is None
                                     else by[(a, *k)][f"{mp}_{q}"]) for k in keys],
                                    dtype=float)
                       for a in present}
                   for q in ("brier_raw", "brier", "refinement", "calibration",
                             "uncertainty", "auc", "auprc", "auprc_minority",
                             "type_I_vol", "type_II_vol", "total_error_vol", "vol")}
            # nanmean, because AUC/AUPRC are undefined (nan/None) when a class is
            # absent and fi/iou are nan for an empty region. `n_defined` travels with
            # every mean so a number averaged over fewer campaigns is visible as one.
            means = {q: {a: float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
                         for a, v in vec[q].items()} for q in vec}
            n_defined = {q: {a: int(np.isfinite(v).sum()) for a, v in vec[q].items()}
                         for q in vec}
            # Uncertainty is a function of (truth, tau) alone, so its across-arm spread
            # must be exactly 0. A nonzero value means the arms were not scored against
            # the same truth, which would invalidate every comparison below.
            spread = {q: max(means[q].values()) - min(means[q].values()) for q in means}
            rank_brier = _order(present, means["brier_raw"], higher_is_better=False)
            rank_ref = _order(present, means["refinement"], higher_is_better=True)
            # The registered question is about the sum the project has PUBLISHED, which
            # is the raw Brier, so that is what `rank_brier` uses. The binned Brier is
            # what the identity actually decomposes, so its ranking is carried too: if
            # the two Brier rankings coincide, the binned/raw distinction is immaterial
            # to the verdict and can be said to be, rather than assumed.
            rank_binned = _order(present, means["brier"], higher_is_better=False)
            # AMENDMENT F2's own decision rule: if the error-volume ranking differs from
            # the AUC ranking, the ERROR-VOLUME ranking is the reported one and AUC is
            # retained beside it as superseded. If they agree, AUC is vindicated AT THIS
            # IMBALANCE, and the prevalence is stated with it.
            rank_auc = _order(present, means["auc"], higher_is_better=True)
            rank_err = _order(present, means["total_error_vol"], higher_is_better=False)
            rank_auprc = _order(present, means["auprc_minority"], higher_is_better=True)
            inversions = [[a, b] for a, b in itertools.combinations(present, 2)
                          if ((rank_brier.index(a) < rank_brier.index(b))
                              != (rank_ref.index(a) < rank_ref.index(b)))]
            # The registered rule is a boolean, and with 6 arms x 15 pairs x 24 cells a
            # bare boolean will find SOME inversion by chance. The rank correlation and
            # the paired tests below are what say whether it is real. Reported beside
            # the registered verdict, never instead of it.
            from scipy.stats import kendalltau, spearmanr
            ref_v = [means["refinement"][a] for a in present]
            neg_b = [-means["brier_raw"][a] for a in present]
            agreement = {"spearman_rho": float(spearmanr(ref_v, neg_b).statistic),
                         "kendall_tau": float(kendalltau(ref_v, neg_b).statistic),
                         "n_pair_inversions": len(inversions),
                         "n_pairs": len(present) * (len(present) - 1) // 2}
            cell[mp] = {"means": means, "n_defined": n_defined,
                        "across_arm_spread": spread,
                        "agreement": agreement,
                        "mean_within_bin": {a: float(np.mean(
                            [by[(a, *k)][f"{mp}_within_bin"] for k in keys]))
                            for a in present},
                        "rank_by_brier": rank_brier,
                        "rank_by_brier_binned": rank_binned,
                        "binned_brier_ranks_as_raw": rank_binned == rank_brier,
                        "rank_by_refinement": rank_ref,
                        "rankings_agree": rank_brier == rank_ref,
                        "inversions": inversions,
                        "rank_by_auc": rank_auc,
                        "rank_by_error_volume": rank_err,
                        "rank_by_auprc_minority": rank_auprc,
                        "error_volume_agrees_with_auc": rank_err == rank_auc,
                        "auprc_agrees_with_auc": rank_auprc == rank_auc}
            for a, b in inversions:
                tests.append({"gamma": gamma, "tau_frac": tf, "map": mp,
                              "pair": [a, b],
                              "refinement": dual_paired_stats(vec["refinement"][a],
                                                              vec["refinement"][b], keys),
                              "brier_raw": dual_paired_stats(vec["brier_raw"][a],
                                                             vec["brier_raw"][b], keys)})
        cells.append(cell)

    # Holm across the cells, separately at each unit -- an adjustment computed across a
    # mixture of units would not be an adjustment for either.
    for mp in ("pred", "latent"):
        idx = [i for i, t in enumerate(tests) if t["map"] == mp]
        for unit in ("n50", "n25"):
            if idx:
                adj = _holm([tests[i]["refinement"][unit]["wilcoxon_p"] for i in idx])
                for i, a in zip(idx, adj):
                    tests[i]["refinement"][unit]["holm_p"] = a
    for t in tests:
        # F1: significant at n=50 and not at n=25 is NOT a finding.
        t["survives_conservative_unit"] = bool(
            t["refinement"]["n25"].get("holm_p", 1.0) < 0.05)

    scored = [c for c in cells if "pred" in c]
    disagree = {mp: [[c["gamma"], c["tau_frac"]] for c in scored
                     if not c[mp]["rankings_agree"]] for mp in ("pred", "latent")}
    sig = {u: sum(1 for t in tests if t["map"] == "pred"
                  and t["refinement"][u].get("holm_p", 1.0) < 0.05)
           for u in ("n50", "n25")}
    n_inv = sum(1 for t in tests if t["map"] == "pred")
    if not disagree["pred"]:
        verdict = ("A5 IS A NULL — refinement ranks the arms exactly as Brier does at "
                   "every scored cell")
    elif sig["n25"] == 0:
        verdict = (f"A5 IS A NULL AT THE CONSERVATIVE UNIT — the two rankings differ at "
                   f"{len(disagree['pred'])} of {len(scored)} predictive-map cells, but "
                   f"NONE of the {n_inv} inverted pairs survives Holm at n=25 "
                   f"({sig['n50']} survive at the anti-conservative n=50). Per Amendment "
                   f"F1, n=25 governs and a difference significant only at n=50 is not a "
                   f"finding.")
    else:
        verdict = (f"A5 FOUND SOMETHING — the two rankings differ at "
                   f"{len(disagree['pred'])} of {len(scored)} predictive-map cells, and "
                   f"{sig['n25']} of {n_inv} inverted pairs survive Holm at the "
                   f"conservative unit n=25 ({sig['n50']} at n=50)")
    flags = {f: sum(1 for r in rows for mp in ("pred", "latent")
                    if f in r[f"{mp}_degenerate"])
             for f in ("single_class", "few_bins", "singleton_bin")}
    worst_unc_spread = max((c[mp]["across_arm_spread"]["uncertainty"]
                            for c in cells if "pred" in c for mp in ("pred", "latent")),
                           default=0.0)
    return {"cells": cells, "inversion_tests": tests,
            "n_inversions_surviving_holm": sig, "n_inversion_tests_pred": n_inv,
            "degenerate_flag_counts": flags,
            "worst_uncertainty_across_arm_spread": worst_unc_spread,
            "cells_where_rankings_differ": disagree,
            "n_cells_scored": len(scored), "verdict": verdict,
            "verdict_map": "pred (Peterson D_gamma, the primary object)"}


def _print_summary(s: dict) -> None:
    print(f"\n{'gamma':>6} {'tauf':>5} {'n':>4} {'drop':>4} {'prev':>8}  "
          f"{'pred':>5}  rank_by_brier -> rank_by_refinement")
    for c in s["cells"]:
        if "pred" not in c:
            print(f"{c['gamma']:6.2f} {c['tau_frac']:5.2f} {c['n_used']:4d} "
                  f"{c['n_single_class_dropped']:4d}   {c.get('verdict', '')}")
            continue
        p = c["pred"]
        flag = "SAME " if p["rankings_agree"] else "DIFF "
        print(f"{c['gamma']:6.2f} {c['tau_frac']:5.2f} {c['n_used']:4d} "
              f"{c['n_single_class_dropped']:4d} {c['mean_prevalence']:8.5f}  {flag}  "
              f"{' '.join(p['rank_by_brier'])}  ->  {' '.join(p['rank_by_refinement'])}")
    scored = [c for c in s["cells"] if "pred" in c]
    if scored:
        rho = [c["pred"]["agreement"]["spearman_rho"] for c in scored]
        inv = [c["pred"]["agreement"]["n_pair_inversions"] for c in scored]
        print(f"\npredictive map, refinement vs Brier across the {len(scored)} cells: "
              f"Spearman rho min {min(rho):+.3f} median {float(np.median(rho)):+.3f} "
              f"max {max(rho):+.3f}; pair inversions {sum(inv)} of "
              f"{sum(c['pred']['agreement']['n_pairs'] for c in scored)}")
    print(f"latent-map cells differing: {len(s['cells_where_rankings_differ']['latent'])}"
          f" of {s['n_cells_scored']}")
    if scored:
        n_same = sum(1 for c in scored if c["pred"]["binned_brier_ranks_as_raw"])
        print(f"binned Brier ranks the arms as the raw Brier does at {n_same} of "
              f"{len(scored)} cells")
    if scored:
        n_ev = sum(1 for c in scored if c["pred"]["error_volume_agrees_with_auc"])
        n_ap = sum(1 for c in scored if c["pred"]["auprc_agrees_with_auc"])
        print(f"F2 rule — error-volume ranking agrees with AUC at {n_ev} of "
              f"{len(scored)} cells; AUPRC(minority) agrees with AUC at {n_ap}")
        print(f"F1 — inverted pairs surviving Holm: n=50 "
              f"{s['n_inversions_surviving_holm']['n50']}, n=25 "
              f"{s['n_inversions_surviving_holm']['n25']}, of "
              f"{s['n_inversion_tests_pred']}")
    print(f"degenerate flags fired: {s['degenerate_flag_counts']}")
    print("worst across-arm uncertainty spread (must be 0.0): "
          f"{s['worst_uncertainty_across_arm_spread']:.3e}")
    print(f"\n*** {s['verdict']} ***")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to score; default all 50")
    ap.add_argument("--arms", type=str, default=None, help="comma-separated subset")
    ap.add_argument("--out", type=str, default=None, help="default results/p7-murphy.json")
    ap.add_argument("--summarise", type=str, default=None,
                    help="recompute the summary of an existing file and write it back; "
                         "refuses on a git-tracked file, and never touches `rows`")
    ap.add_argument("--resume", action="store_true",
                    help="continue an interrupted run; refuses on a git-tracked file")
    args = ap.parse_args()

    if args.summarise:
        path = Path(args.summarise)
        doc = json.loads(path.read_text())
        summary = summarise(doc["rows"])
        _print_summary(summary)
        if _is_tracked(path):
            print(f"\n{path} is tracked by git — printed only, nothing written.")
        else:
            doc["summary"] = summary
            path.write_text(json.dumps(doc, indent=1))
            print(f"\nsummary refreshed in {path}")
        return

    global ARMS, OUT, CKPT
    if args.arms:
        ARMS = tuple(a.strip() for a in args.arms.split(","))
    if args.out:
        OUT = Path(args.out)
        CKPT = OUT.with_suffix(".partial.json")
    prior = None
    if OUT.exists():
        sys.exit(f"{OUT} exists. A finished result is never overwritten; "
                 f"pass --out for a smoke run, or delete it if it is not the real one.")
    if args.resume:
        if not CKPT.exists():
            sys.exit(f"--resume needs {CKPT}, which does not exist.")
        if _is_tracked(CKPT):
            sys.exit(f"{CKPT} is tracked by git. A committed result is never rewritten.")
        prior = json.loads(CKPT.read_text())

    print(f"P7 · Murphy decomposition · HEAD={_git('rev-parse', 'HEAD')[:8]} · "
          f"python={platform.python_version()}")
    print(f"cell hill d={DIM} sigma_rel={SIGMA} · arms={ARMS}")
    print(f"gamma={GAMMAS}\ntau_frac={TAU_FRACS} · {N_BINS} equal-count bins")
    print(f"grid: {GRID_N} Sobol at seed {GRID_SEED}\n")

    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == DIM and r["sigma"] == SIGMA and r["arm"] == "qlogei"})
    if args.limit:
        keys = keys[:args.limit]
    print(f"{len(keys)} (instance, seed) pairs x {len(ARMS)} arms "
          f"= {len(keys) * len(ARMS)} campaigns\n")

    committed = {(r["instance"], r["seed"], r["arm"]): r["regret"] for r in committed_rows()
                 if r["dim"] == DIM and r["sigma"] == SIGMA}
    committed_b = _committed_maps()
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)

    rows: list[dict] = []
    gate_fail: list[dict] = []
    map_fail: list[dict] = []
    identity_fail: list[dict] = []
    worst_identity = 0.0
    worst_map = {c: 0.0 for c in GATED_COLUMNS}
    n_map_checked = 0
    done: set[tuple[str, int]] = set()
    if prior is not None:
        rows = prior["rows"]
        gate_fail, map_fail = prior["gate_failures"], prior["map_gate"]["failures"]
        identity_fail = prior["identity"]["failures"]
        worst_identity = prior["identity"]["max_residual"]
        worst_map = prior["map_gate"]["worst_abs_delta"]
        n_map_checked = prior["map_gate"]["rows_checked"]
        # A pair is resumable only if it carries a FULL set of rows: the file is written
        # after every arm of a pair finishes, so a short pair means a truncated write.
        seen: dict[tuple[str, int], int] = {}
        for r in rows:
            seen[(r["instance"], r["seed"])] = seen.get((r["instance"], r["seed"]), 0) + 1
        full = len(ARMS) * len(GAMMAS) * len(TAU_FRACS)
        done = {k for k, n in seen.items() if n == full}
        rows = [r for r in rows if (r["instance"], r["seed"]) in done]
        print(f"resuming: {len(done)} of {len(keys)} pairs already scored, "
              f"{len(rows)} rows kept\n")
    t0 = time.time()

    for i, (inst_id, seed) in enumerate(keys, 1):
        if (inst_id, seed) in done:
            continue
        inst = instance_by_id(inst_id, DIM)
        orc = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
        with torch.no_grad():
            truth = orc.truth(grid).reshape(-1).double()

        for arm in ARMS:
            t = time.time()
            rec = regenerate(inst_id, DIM, SIGMA, seed, arm)

            ref = committed.get((inst_id, seed, arm))
            if ref is None:
                gate_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                  "reason": "no committed regret column"})
                print(f"  !! UNGATED {arm} {inst_id} seed={seed}")
            else:
                delta = abs(rec.regret - ref)
                if delta > _gate_tol(arm):
                    gate_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                      "committed": ref, "regenerated": rec.regret,
                                      "abs_delta": delta})
                    print(f"  !! GATE {arm} {inst_id} seed={seed} delta={delta:.3e}")

            new, fails, worst = score_campaign(rec, orc, grid, truth)
            rows.extend(new)
            identity_fail.extend(fails)
            worst_identity = max(worst_identity, worst)

            for r in new:
                key = (inst_id, seed, arm, r["gamma"], r["tau_frac"])
                if key not in committed_b:
                    continue
                n_map_checked += 1
                for col, cb in committed_b[key].items():
                    mine = r[MINE_FOR[col]]
                    if _same(mine, cb):
                        continue
                    d = abs(mine - cb)
                    worst_map[col] = max(worst_map.get(col, 0.0), d)
                    map_fail.append({"instance": inst_id, "seed": seed, "arm": arm,
                                     "gamma": r["gamma"], "tau_frac": r["tau_frac"],
                                     "column": col, "committed": cb, "regenerated": mine,
                                     "abs_delta": d})
            print(f"[{i:3d}/{len(keys)}] {arm:8s} {inst_id} seed={seed} "
                  f"regret={rec.regret:.4f} rows={len(new)} ({time.time() - t:.1f}s)",
                  flush=True)

        CKPT.write_text(json.dumps(result_document(
            "partial", len({(r["instance"], r["seed"]) for r in rows}), len(keys),
            sys.argv, gate_fail, map_fail, worst_map, n_map_checked, identity_fail,
            worst_identity, rows), indent=1))
        del truth
        gc.collect()

    # Promote ONCE, whole, and only now. Everything above this line lived at CKPT.
    summary = summarise(rows)
    n_keys = len({(r["instance"], r["seed"]) for r in rows})
    final = result_document("complete", n_keys, len(keys), sys.argv, gate_fail, map_fail,
                    worst_map, n_map_checked, identity_fail, worst_identity, rows)
    final["summary"] = summary
    if n_keys != len(keys):
        final["status"] = "partial"
        print(f"*** {n_keys} of {len(keys)} keys scored — writing status=partial ***")
    OUT.write_text(json.dumps(final, indent=1))
    CKPT.unlink(missing_ok=True)

    print(f"\n{len(rows)} scored rows in {time.time() - t0:.0f}s")
    print(f"regret gate failures: {len(gate_fail)}")
    print(f"map gate: {n_map_checked} rows x {len(GATED_COLUMNS)} committed columns, "
          f"worst |delta| {max(worst_map.values()):.3e}, {len(map_fail)} failures")
    print(f"  (ERRATUM 2) recomputed at torch_threads={torch.get_num_threads()} against "
          f"columns produced at the default")
    print(f"identity: max residual {worst_identity:.3e} against bar {IDENTITY_BAR:.0e}, "
          f"{len(identity_fail)} rows withheld")
    _print_summary(summary)
    if gate_fail or map_fail or identity_fail:
        print("\n*** A gate failed. Halt and report, do not repair (stop condition 1). ***")
        sys.exit(1)


if __name__ == "__main__":
    main()
