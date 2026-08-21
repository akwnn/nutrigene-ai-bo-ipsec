"""Amendment F2a / F2c — expected type I / type II error volumes, and IoU and Brier ranked.

    .venv/bin/python scripts/analyse_f2_error_volumes.py

Reads the committed design-space blobs through `git show HEAD:<path>`; writes
`results/f2-error-volumes.json`. **No campaign is run.** Every number is derived from
columns that have been on disk since K6 ran.

F2a — WHY AUC IS THE WRONG PRIMARY
----------------------------------
AUC is invariant to any monotone transformation of the score, so it measures *ranking* and
can never measure *calibration* — and a design space is a calibrated absolute statement
about which settings are acceptable, not a ranking of grid points. The evidence that this
matters is already committed: mean `grid_r2` is **negative for all eight arms**, i.e. the
posterior mean is a worse point predictor than the constant grid mean, for every arm. AUC
cannot see that. The excursion-set literature (Azzimonti & Ginsbourger 2018, Table 1)
reports expected type I and type II error volumes, Vorob'ev deviation and IoU — not AUC.

The derivation, from columns already committed:

    type_I_vol  = vol_pred * fi_pred                      # |D_est \\ D_true| / |grid|
    intersect   = vol_pred * (1 - fi_pred)
    type_II_vol = true_frac_above_tau - intersect         # |D_true \\ D_est| / |grid|

and the `_latent` counterparts. The check on the algebra is that
`intersect / (vol + prevalence - intersect)` reproduces the committed `iou_*`; see
`tests/test_f2_error_volumes.py`, which asserts the registered figures rather than
whatever this code produces.

AND THEY ARE DEFINED WHERE THE FALSE-INCLUSION RATE IS NOT
-----------------------------------------------------------
When `D_est` is empty, `fi` is 0/0 and unusable. The error volumes are not: nothing was
claimed, so type I is exactly 0, and the whole true set was missed, so type II is exactly
the prevalence. Both are correct rather than merely defined. That is why the scorable-row
count rises from the 2,553 that `fi_pred` admits to all 6,000.

**One correction to the registration, recorded because it changes what may be claimed.**
F2a states that `fi_pred` and `iou_pred` are both `nan` when `D_est` is empty. Only
`fi_pred` is. `iou_pred` is committed as **0.0** on all 3,447 empty rows, which is the
right value (an empty intersection over a non-empty union), so IoU does *not* break where
the registration says it does. The claim survives for the false-inclusion rate and fails
for IoU, and only the surviving half is used below.

F2c — IoU AND BRIER ARE COMMITTED PER ROW AND NOTHING RANKS ON THEM
--------------------------------------------------------------------
`scripts/analyse_k6.py` ranks on `auc_pred` and on neither `iou_*` nor `brier_*`, though
both sit on every one of the 9,600 committed rows. Pure analysis gap; this closes it, at
both units per F1.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_f1_dual_n import dual_contrast  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "f2-error-volumes.json"

#: The three committed columns the derivation needs. `{suffix}` is `pred` or `latent`.
REQUIRED_COLUMNS = ("vol_{suffix}", "fi_{suffix}", "true_frac_above_tau")
SUFFIXES = ("pred", "latent")

#: Every committed design-space file, per the registration.
DESIGN_SPACE_FILES = ("results/k6-designspace.json",
                      "results/k6-designspace-spread.json",
                      "results/versionb.json",
                      "results/versionb-predictive.json")

#: Ranked lower-is-better. `total` is the symmetric-difference volume |D_est ^ D_true|.
VOLUME_METRICS = ("type_I", "type_II", "total")


def committed_rows(path: str) -> list[dict]:
    """Rows of a committed blob at HEAD, not from the working tree.

    Six agents are writing into `results/` concurrently.
    """
    blob = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout
    return json.loads(blob)["rows"]


def missing_columns(rows: list[dict], suffixes=SUFFIXES) -> tuple[str, ...]:
    """Which required columns this file does not carry.

    A file that lacks them is a **finding**, not a hole to fill: the registration is
    explicit that the prevalence must not be imputed from another file, because the
    prevalence is a property of the campaign's own evaluation grid.
    """
    have = set(rows[0]) if rows else set()
    want = {c.format(suffix=s) for c in REQUIRED_COLUMNS for s in suffixes}
    return tuple(sorted(c for c in want if c not in have))


def error_volumes(rows: list[dict], suffix: str) -> dict[str, np.ndarray]:
    """Expected type I / type II error volumes for one labelling of the grid.

    Raises `KeyError` naming what is absent rather than producing a plausible number from
    an imputed prevalence.
    """
    need = [c.format(suffix=suffix) for c in REQUIRED_COLUMNS]
    absent = [c for c in need if rows and c not in rows[0]]
    if absent:
        raise KeyError(f"columns absent, error volumes are not computable: {absent}")
    vol = np.array([r[f"vol_{suffix}"] for r in rows], dtype=float)
    fi = np.array([r[f"fi_{suffix}"] for r in rows], dtype=float)
    prev = np.array([r["true_frac_above_tau"] for r in rows], dtype=float)

    fi_defined = np.isfinite(fi)
    # An empty D_est claims nothing: no false inclusion, and the whole true set is missed.
    type_I = np.where(fi_defined, vol * np.nan_to_num(fi, nan=0.0), 0.0)
    intersect = np.where(fi_defined, vol * (1.0 - np.nan_to_num(fi, nan=0.0)), 0.0)
    type_II = prev - intersect
    union = vol + prev - intersect
    with np.errstate(invalid="ignore", divide="ignore"):
        iou_derived = np.where(union > 0, intersect / union, np.nan)
    return {"vol": vol, "prevalence": prev, "fi_defined": fi_defined,
            "type_I": type_I, "intersect": intersect, "type_II": type_II,
            "total": type_I + type_II, "iou_derived": iou_derived,
            "empty": ~fi_defined}


# ------------------------------------------------------------------------------ ranking
def _arm_means(rows, values, arms):
    """Descriptive arm means. NOT an inferential summary and carries no `n` (F4)."""
    idx = {a: np.array([r["arm"] == a for r in rows]) for a in arms}
    return {a: float(np.mean(values[idx[a]])) if idx[a].any() else float("nan")
            for a in arms}


def _rank(scores: dict, lower_is_better: bool) -> list[str]:
    good = [a for a, v in scores.items() if np.isfinite(v)]
    return sorted(good, key=lambda a: scores[a] if lower_is_better else -scores[a])


def _degenerate(scores: dict) -> bool:
    """Every arm scoring identically. The ordering is then an artefact of the sort.

    This is not hypothetical: at `tau_frac = 0.95` every predictive region is empty in
    100% of campaigns, so every arm has type I exactly 0 and type II exactly the
    prevalence, and 'the ranking' there means nothing. Flagged rather than ranked.
    """
    v = np.array([x for x in scores.values() if np.isfinite(x)], dtype=float)
    return bool(v.size and float(v.max() - v.min()) <= 1e-15)


def _concordance(auc: dict, vol: dict) -> float:
    """Spearman rho between the AUC ordering and a lower-is-better ordering.

    +1 means the two metrics order the arms identically, -1 exactly oppositely. Reported
    because 'the two 8-arm orderings are not literally equal' is nearly uninformative --
    there are 40,320 of them -- while 'they are reversed' is the whole finding.
    """
    arms = [a for a in auc if np.isfinite(auc[a]) and np.isfinite(vol.get(a, np.nan))]
    if len(arms) < 3:
        return float("nan")
    x = np.array([-auc[a] for a in arms])          # negate: lower is better, as volumes are
    y = np.array([vol[a] for a in arms])
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def _provenance() -> dict:
    def v(pkg):
        try:
            return version(pkg)
        except PackageNotFoundError:
            return None
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip())
    return {"git_sha": sha, "git_dirty": dirty,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"),
            "argv": sys.argv, "python": platform.python_version(),
            "numpy": v("numpy"), "scipy": v("scipy"),
            "torch": v("torch"), "botorch": v("botorch"), "gpytorch": v("gpytorch"),
            "reads": "committed blobs via `git show HEAD:<path>`; no campaign is run"}


def main() -> None:
    RULE = "=" * 112
    out = {"provenance": _provenance(),
           "amendment": "F2a (error volumes primary) and F2c (rank on IoU and Brier), "
                        "commit 07e98df",
           "derivation": {c: c for c in REQUIRED_COLUMNS} | {
               "type_I_vol": "vol * fi",
               "intersect": "vol * (1 - fi)",
               "type_II_vol": "true_frac_above_tau - intersect",
               "empty_D_est": "fi is 0/0; type_I = 0 and type_II = prevalence, both exact"},
           "files": {}}

    print(f"{RULE}\nAMENDMENT F2a — EXPECTED TYPE I / TYPE II ERROR VOLUMES AS THE "
          f"PRIMARY DESIGN-SPACE METRIC\n{RULE}")

    # -- 1. which committed files can carry the derivation at all ---------------------
    print("\n1. WHICH COMMITTED DESIGN-SPACE FILES CARRY THE COLUMNS")
    print("   A file that does not is a finding. The prevalence is a property of the "
          "campaign's own\n   evaluation grid and must not be imputed from another file.")
    usable = {}
    for path in DESIGN_SPACE_FILES:
        rows = committed_rows(path)
        absent = missing_columns(rows)
        rec = {"n_rows": len(rows), "computable": not absent,
               "missing_columns": list(absent)}
        if absent:
            rec["finding"] = ("error volumes are NOT computable for this file; the "
                              "prevalence is not imputed from another file")
        else:
            usable[path] = rows
        out["files"][path] = rec
        mark = "yes" if not absent else "NO"
        print(f"   {path:<44} rows={len(rows):>5}  computable={mark}"
              + (f"\n{'':>50}missing: {', '.join(absent)}" if absent else ""))

    # -- 2. the registered validation --------------------------------------------------
    k6 = usable["results/k6-designspace.json"]
    ev = error_volumes(k6, "pred")
    iou_committed = np.array([r["iou_pred"] for r in k6], dtype=float)
    m = ev["fi_defined"]
    worst = float(np.max(np.abs(ev["iou_derived"][m] - iou_committed[m])))
    neg = int((ev["type_II"] < 0).sum())
    out["registered_validation"] = {
        "file": "results/k6-designspace.json", "suffix": "pred",
        "scorable_rows": int(m.sum()), "registered_scorable_rows": 2553,
        "worst_abs_delta_vs_committed_iou": worst,
        "registered_worst_abs_delta": 2.220e-16,
        "negative_type_II_volumes": neg,
        "reproduces": bool(int(m.sum()) == 2553 and worst <= 1e-15 and neg == 0)}
    print(f"\n2. THE REGISTERED VALIDATION (the check on the algebra)")
    print(f"   derived IoU vs committed `iou_pred`: worst |delta| = {worst:.3e} over "
          f"{int(m.sum())} rows")
    print(f"   registered: 2.220e-16 over 2,553 rows, zero negative type-II volumes")
    print(f"   negative type-II volumes: {neg}    "
          f"REPRODUCES: {out['registered_validation']['reproduces']}")

    # -- 3. scorable-row counts, and the emptiness that sits beside them ---------------
    print(f"\n3. SCORABLE ROWS — the error volumes are defined where the false-inclusion "
          f"rate is not")
    counts = {}
    for path, rows in usable.items():
        for suffix in SUFFIXES:
            e = error_volumes(rows, suffix)
            fi_n = int(e["fi_defined"].sum())
            iou_n = int(np.isfinite(
                np.array([r[f"iou_{suffix}"] for r in rows], dtype=float)).sum())
            counts[f"{Path(path).stem}:{suffix}"] = {
                "rows": len(rows), "error_volumes": len(rows),
                "false_inclusion_rate": fi_n, "committed_iou": iou_n,
                "empty_D_est": len(rows) - fi_n,
                "empty_frac": float(1 - fi_n / len(rows))}
            print(f"   {Path(path).stem:<28} {suffix:<7} rows={len(rows):>5}  "
                  f"error-vol scorable={len(rows):>5}  fi scorable={fi_n:>5}  "
                  f"committed IoU finite={iou_n:>5}  empty={1 - fi_n / len(rows):>6.1%}")
    out["scorable_rows"] = counts
    out["emptiness_note"] = (
        "Reported beside the volumes regardless, per F2a. NOTE the correction: only "
        "`fi_*` is nan on an empty D_est; the committed `iou_*` is 0.0 there and is "
        "finite on every row, so IoU does not break where the registration says it does.")

    # -- 4. THE RANKING: error volumes against AUC -------------------------------------
    k6_rows = k6 + usable["results/k6-designspace-spread.json"]
    cfg = json.loads(subprocess.run(
        ["git", "show", "HEAD:results/k6-designspace.json"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)["config"]
    gammas, tau_fracs = cfg["gammas"], cfg["tau_fracs"]
    arms = sorted({r["arm"] for r in k6_rows})

    print(f"\n{RULE}\n4. THE REGISTERED DECISION — does the error-volume ranking differ "
          f"from AUC's?\n{RULE}")
    print("   Error volumes: LOWER is better. AUC: HIGHER is better. Both descriptive "
          "arm means over\n   the cell's 400 rows; no n and no p is attached to a "
          "ranking (F4).")
    cells, agree = [], {m: 0 for m in VOLUME_METRICS}
    degen = {m: 0 for m in VOLUME_METRICS}
    for g in gammas:
        for tf in tau_fracs:
            sub = [r for r in k6_rows if r["gamma"] == g and r["tau_frac"] == tf]
            e = error_volumes(sub, "pred")
            auc = _arm_means(sub, np.array([r["auc_pred"] for r in sub], dtype=float), arms)
            auc_rank = _rank(auc, lower_is_better=False)
            rec = {"gamma": g, "tau_frac": tf,
                   "prevalence": float(np.mean(e["prevalence"])),
                   "empty_frac": float(np.mean(e["empty"])),
                   "auc_pred": auc, "auc_rank": auc_rank}
            for metric in VOLUME_METRICS:
                means = _arm_means(sub, e[metric], arms)
                rank = _rank(means, lower_is_better=True)
                rec[f"{metric}_vol"] = means
                rec[f"{metric}_rank"] = rank
                rec[f"{metric}_degenerate"] = _degenerate(means)
                rec[f"{metric}_spearman_vs_auc"] = _concordance(auc, means)
                rec[f"{metric}_agrees_with_auc"] = bool(
                    rank == auc_rank and not rec[f"{metric}_degenerate"])
                agree[metric] += rec[f"{metric}_agrees_with_auc"]
                degen[metric] += rec[f"{metric}_degenerate"]
            cells.append(rec)
    out["cells"] = cells
    print(f"\n   Spearman rho against the AUC ordering: +1 identical, -1 exactly "
          f"reversed.\n   `tie` = every arm scores identically, so there is no ranking "
          f"to compare.\n")
    print(f"   {'gamma':>5} {'tauF':>5} {'prev':>7} {'empty':>6}  "
          f"{'rho typeI':>10} {'rho typeII':>11} {'rho total':>10}  {'tie':>5}")
    for c in cells:
        tie = "  ".join("T" if c[f"{m}_degenerate"] else "." for m in VOLUME_METRICS)
        def _r(m):
            v = c[f"{m}_spearman_vs_auc"]
            return "     --" if not np.isfinite(v) else f"{v:>+6.3f}"
        print(f"   {c['gamma']:>5.2f} {c['tau_frac']:>5.2f} {c['prevalence']:>7.4f} "
              f"{c['empty_frac']:>6.1%}  {_r('type_I'):>10} {_r('type_II'):>11} "
              f"{_r('total'):>10}  {tie:>5}")
    for metric in VOLUME_METRICS:
        rhos = np.array([c[f"{metric}_spearman_vs_auc"] for c in cells], dtype=float)
        rhos = rhos[np.isfinite(rhos)]
        print(f"   {metric:>8}: equals the AUC ranking in {agree[metric]}/{len(cells)} "
              f"cells · degenerate ties in {degen[metric]} · median rho "
              f"{np.median(rhos) if rhos.size else float('nan'):+.3f}")

    # The across-cell descriptive ranking, at the primary labelling.
    e_all = error_volumes(k6_rows, "pred")
    auc_all = _arm_means(k6_rows,
                         np.array([r["auc_pred"] for r in k6_rows], dtype=float), arms)
    overall = {"auc_pred": auc_all, "auc_rank": _rank(auc_all, False)}
    for metric in VOLUME_METRICS:
        means = _arm_means(k6_rows, e_all[metric], arms)
        overall[f"{metric}_vol"] = means
        overall[f"{metric}_rank"] = _rank(means, True)
        overall[f"{metric}_agrees_with_auc"] = bool(
            overall[f"{metric}_rank"] == overall["auc_rank"])
        overall[f"{metric}_spearman_vs_auc"] = _concordance(auc_all, means)
    out["overall_ranking"] = overall
    print(f"\n   Across all 24 cells (descriptive, no n):")
    print(f"     AUC(pred), best first : {' > '.join(overall['auc_rank'])}")
    for metric in VOLUME_METRICS:
        vols, order = overall[f"{metric}_vol"], overall[f"{metric}_rank"]
        detail = "  ".join(f"{a}={vols[a]:.4f}" for a in order)
        print(f"     {metric + ' vol':<21}: {' < '.join(order)}")
        print(f"     {'':21}  {detail}")
        print(f"     {'':21}  Spearman vs AUC: "
              f"{overall[f'{metric}_spearman_vs_auc']:+.3f}")

    differs = [m for m in VOLUME_METRICS if not overall[f"{m}_agrees_with_auc"]]
    out["decision"] = {
        "rankings_differ": bool(differs),
        "differ_on": differs,
        "per_cell_agreement": {m: f"{agree[m]}/{len(cells)}" for m in VOLUME_METRICS},
        "per_cell_degenerate_ties": {m: degen[m] for m in VOLUME_METRICS},
        "spearman_vs_auc_overall": {m: overall[f"{m}_spearman_vs_auc"]
                                    for m in VOLUME_METRICS},
        "type_I_alone_rewards_claiming_nothing": (
            "An arm that certifies the empty set has type I volume exactly 0, so type I "
            "read alone ranks silence first. `doe` places 2nd on type I while placing "
            "LAST on type II and on the symmetric difference, and its predictive region "
            "is empty in a majority of campaigns. Azzimonti & Ginsbourger report both; "
            "so does this. `total` is the honest single scalar."),
        "registered_rule": (
            "If the arm ranking under error volumes differs from the ranking under AUC, "
            "the error-volume ranking is the reported one and AUC's is retained beside "
            "it as superseded. If they agree, AUC is vindicated AT THIS IMBALANCE and "
            "that is stated with the prevalence attached."),
        "prevalence_range": [float(min(c["prevalence"] for c in cells)),
                             float(max(c["prevalence"] for c in cells))],
        "reported_ranking": ("error volumes" if differs else "AUC, vindicated at this "
                             "imbalance")}
    print(f"\n   REGISTERED DECISION: error-volume and AUC rankings "
          f"{'DIFFER' if differs else 'AGREE'}"
          f"{' on ' + ', '.join(differs) if differs else ''}.")
    print(f"   -> reported ranking: {out['decision']['reported_ranking']}"
          f"   (prevalence spans {out['decision']['prevalence_range'][0]:.4f}"
          f"-{out['decision']['prevalence_range'][1]:.4f})")

    # -- 5. F2c: rank on IoU and Brier ------------------------------------------------
    print(f"\n{RULE}\n5. AMENDMENT F2c — IoU AND BRIER, COMMITTED PER ROW AND RANKED BY "
          f"NOTHING\n{RULE}")
    print("   `scripts/analyse_k6.py` ranks on `auc_pred` and on neither. Both sit on "
          "all 9,600 rows.")
    f2c = {"per_cell": [], "overall": {}}
    metrics = [("iou_pred", False), ("iou_latent", False),
               ("brier_pred", True), ("brier_latent", True)]
    for g in gammas:
        for tf in tau_fracs:
            sub = [r for r in k6_rows if r["gamma"] == g and r["tau_frac"] == tf]
            rec = {"gamma": g, "tau_frac": tf}
            for key, lower in metrics:
                means = _arm_means(sub, np.array([r[key] for r in sub], dtype=float), arms)
                rec[key] = means
                rec[f"{key}_rank"] = _rank(means, lower)
            f2c["per_cell"].append(rec)
    for key, lower in metrics:
        means = _arm_means(k6_rows, np.array([r[key] for r in k6_rows], dtype=float), arms)
        rank = _rank(means, lower)
        f2c["overall"][key] = {"means": means, "rank": rank,
                               "lower_is_better": lower,
                               "agrees_with_auc": bool(rank == overall["auc_rank"])}
        print(f"   {key:<14} ({'lower' if lower else 'higher'} better), best first: "
              f"{' > '.join(rank)}")
        print(f"   {'':14}  agrees with the AUC ranking: "
              f"{f2c['overall'][key]['agrees_with_auc']}")

    # And the two headline contrasts on those metrics, at both units per F1.
    print(f"\n   The two K6 headline contrasts on IoU and Brier, at both units "
          f"(Wilcoxon p):")
    print(f"   {'contrast':<34}{'metric':<14}{'n50 mean':>10}{'n50 p':>11}"
          f"{'n25 mean':>10}{'n25 p':>11}  status")
    f2c["contrasts"] = []
    for a, b in (("lhs", "doe"), ("doe", "qlogei")):
        for key, _lower in metrics:
            for g, tf in ((gammas[0], tau_fracs[0]), (0.90, 0.75)):
                d = dual_contrast(k6_rows, a, b, key, gamma=g, tau_frac=tf)
                d["label"] = f"{a} - {b}"
                d["metric"] = key
                d["gamma"], d["tau_frac"] = g, tf
                f2c["contrasts"].append(d)
                print(f"   {f'{a} - {b} g={g} tf={tf}':<34}{key:<14}"
                      f"{d['n50']['mean']:>+10.4f}{d['n50']['wilcoxon_p']:>11.2e}"
                      f"{d['n25']['mean']:>+10.4f}{d['n25']['wilcoxon_p']:>11.2e}"
                      f"  {d['status_n50']}/{d['status_n25']}")
    f2c["note_on_units"] = (
        "The design is balanced -- 25 instances x 2 seeds, no nan drops -- so an arm MEAN "
        "is bitwise identical at both units and the RANKINGS above cannot differ between "
        "them. Only the contrasts move, which is where n is doing work.")
    out["f2c"] = f2c
    print(f"\n   {f2c['note_on_units']}")

    OUT.write_text(json.dumps(out, indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
