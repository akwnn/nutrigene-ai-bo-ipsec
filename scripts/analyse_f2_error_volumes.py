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
F2a states that `fi_pred` and `iou_pred` are both `nan` when `D_est` is empty. **The two
conditions are different:**

* `fi` is `nan` whenever **`D_est`** is empty — 3,447 of 6,000 rows here.
* `iou` is `nan` only when the **UNION** is empty, i.e. `D_est` *and* `D_true` both empty.
  An empty `D_est` against a non-empty true set gives IoU = **0**, which is correct.

The error volumes are therefore strictly better defined than IoU — both are fine where
IoU is 0/0 — but **on this data the true excursion set is never empty** (minimum
prevalence 0.0012), so the margin over IoU is **zero rows**. The coverage gain is real
and it is over `fi`, not over IoU. The two counts are reported separately below rather
than as one "IoU/fi break here" figure, and the AUC half of F2a's argument — which was
always the stronger half — is untouched by this.

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyse_f1_dual_n import dual_contrast  # noqa: E402
from boec.calibration import error_volumes as _canonical  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "f2-error-volumes.json"
#: A separate file, never an overwrite: it answers a different question from OUT.
OUT_CE = ROOT / "results" / "f2-ce-error-volumes.json"

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
    """Row-wise adapter over `boec.calibration.error_volumes`.

    **The arithmetic is NOT reimplemented here.** It lived in this file first and was
    deleted when `src/boec/calibration.py` became the canonical home, so that one
    committed quantity has one implementation rather than three. This function only
    vectorises over rows and names the columns.

    The property the local copy had that was worth preserving is the **gate against the
    committed `iou_pred` column**, and that gate moved with the arithmetic: see
    `tests/test_f2_error_volumes.py::
    test_the_registered_gate_holds_against_the_canonical_implementation`, which asserts
    it against the imported function directly. If that test ever fails, the canonical
    implementation has stopped describing the committed sets — stop and report; do not
    patch it from here, `src/boec/` belongs to another workstream.

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

    cols = [_canonical(v, f, p) for v, f, p in zip(vol, fi, prev, strict=True)]
    pull = lambda k: np.array([c[k] for c in cols], dtype=float)  # noqa: E731
    return {"vol": vol, "prevalence": prev,
            # The two nan conditions are DIFFERENT and are counted separately (F2a
            # erratum): `fi` is nan when D_est is empty; `iou` is nan only when the
            # UNION is empty, i.e. D_est and D_true BOTH empty.
            "fi_defined": np.isfinite(fi),
            "empty_d_est": ~np.isfinite(fi),
            "empty_union": (vol == 0) & (prev == 0),
            "type_I": pull("type_I_vol"), "intersect": pull("intersect"),
            "type_II": pull("type_II_vol"), "total": pull("total_error_vol"),
            "iou_derived": pull("implied_iou"),
            "empty": ~np.isfinite(fi)}


def ce_error_volumes(rows: list[dict], alpha: float) -> dict[str, np.ndarray]:
    """Error volumes for the `CE_alpha` sets of K6b — the object the certificate is about.

    Same canonical arithmetic, different inputs: `ce_vol_{alpha}`, `ce_false_in_{alpha}`
    and `true_frac_above`. Extending F2a's primary metric to `CE_alpha` costs nothing
    because all three columns are already committed.

    **Two things are different here from the K6 map, and both bound what may be claimed.**

    1. **There is no committed IoU column for the CE sets**, so this application has no
       independent cross-check of the kind that gates the map derivation. What can still
       be falsified is that the columns share a normalisation — `ce_vol * (1 - fi)`
       exceeding the prevalence would drive type II negative. It does not, in any of
       4,800 (row, alpha) combinations.
    2. **K6b scores `doe` on its own 4-D active subspace** (Amendment B3, §2.8), so the
       prevalence differs by arm within a cell in 198 of 200 cells. The cross-arm ranking
       is therefore **not like-for-like** — the opposite of the K6 map — and `doe`'s slice
       is the easier one, so the bias runs in its favour.
    """
    vol = np.array([r[f"ce_vol_{alpha}"] for r in rows], dtype=float)
    fi = np.array([r[f"ce_false_in_{alpha}"] for r in rows], dtype=float)
    prev = np.array([r["true_frac_above"] for r in rows], dtype=float)
    cols = [_canonical(v, f, p) for v, f, p in zip(vol, fi, prev, strict=True)]
    pull = lambda k: np.array([c[k] for c in cols], dtype=float)  # noqa: E731
    return {"vol": vol, "prevalence": prev,
            "empty": vol == 0, "empty_union": (vol == 0) & (prev == 0),
            "type_I": pull("type_I_vol"), "intersect": pull("intersect"),
            "type_II": pull("type_II_vol"), "total": pull("total_error_vol"),
            "iou_derived": pull("implied_iou")}


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
    print(f"\n3. SCORABLE ROWS — and the TWO nan conditions, counted separately")
    print("   `fi` is nan when D_est is empty. `iou` is nan only when the UNION is empty,")
    print("   i.e. D_est AND D_true both empty. F2a treated them as one condition; they "
          "are not,\n   and the margin over IoU is much smaller than the margin over fi.")
    counts = {}
    for path, rows in usable.items():
        for suffix in SUFFIXES:
            e = error_volumes(rows, suffix)
            fi_n = int(e["fi_defined"].sum())
            iou_n = int(np.isfinite(
                np.array([r[f"iou_{suffix}"] for r in rows], dtype=float)).sum())
            counts[f"{Path(path).stem}:{suffix}"] = {
                "rows": len(rows), "error_volumes_scorable": len(rows),
                "fi_scorable": fi_n, "committed_iou_finite": iou_n,
                "empty_D_est": int(e["empty_d_est"].sum()),
                "empty_union": int(e["empty_union"].sum()),
                "gain_over_fi": len(rows) - fi_n,
                "gain_over_iou": len(rows) - iou_n,
                "empty_frac": float(1 - fi_n / len(rows))}
            print(f"   {Path(path).stem:<28} {suffix:<7} rows={len(rows):>5}  "
                  f"error-vol={len(rows):>5}  fi={fi_n:>5} (+{len(rows) - fi_n})  "
                  f"IoU={iou_n:>5} (+{len(rows) - iou_n})  "
                  f"D_est empty={1 - fi_n / len(rows):>6.1%}  "
                  f"union empty={int(e['empty_union'].sum())}")
    gain_iou = {k: v["gain_over_iou"] for k, v in counts.items()}
    out["scorable_rows"] = counts
    out["emptiness_note"] = (
        "Reported beside the volumes regardless, per F2a. CORRECTION to the "
        "registration, which treated the two nan conditions as one: `fi_*` is nan when "
        "D_est is empty; `iou_*` is nan only when the UNION is empty (D_est and D_true "
        "both empty). On this data D_true is never empty — minimum prevalence 0.0012 — "
        "so the committed `iou_*` is finite on EVERY row and the coverage gain over IoU "
        f"is {max(gain_iou.values())} rows at most. The gain over `fi` is real and large. "
        "F2a's claim that the volumes are defined 'precisely where AUC and IoU break' "
        "holds for the false-inclusion rate and, on this data, not for IoU. The AUC half "
        "of the argument is untouched.")

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
    print("   `prev` = true_frac_above_tau, carried beside every row because a ranking "
          "read without\n   its prevalence inverts. NOTE the gamma direction: gamma "
          "enters tau multiplicatively\n   through tau_max, which DECREASES in gamma, so "
          "HIGH gamma means a LOW absolute\n   threshold and a HUGE positive class. At "
          "gamma=0.99, tau_frac=0.60 prevalence is 0.9992 —\n   the minority class there "
          "is the NEGATIVE one, ~16 of 20,000 points (Erratum 3).")
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

    # -- 6. the SAME primary metric applied to CE_alpha, into a SEPARATE file ----------
    print(f"\n{RULE}\n6. F2a EXTENDED TO `CE_alpha` — the object the SPADE certificate "
          f"is actually about\n{RULE}")
    k6b = committed_rows("results/k6b-conservative.json")
    k6bs = committed_rows("results/k6b-conservative-spread.json")
    k6b_rows = k6b + k6bs
    k6b_cfg = json.loads(subprocess.run(
        ["git", "show", "HEAD:results/k6b-conservative.json"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)["config"]
    k6b_arms = sorted({r["arm"] for r in k6b_rows})
    print("   Zero new campaigns: `ce_vol_*`, `ce_false_in_*` and `true_frac_above` have "
          "all been\n   committed since K6b ran. Same canonical arithmetic, different "
          "inputs.")
    print("   TWO LIMITS. (1) There is NO committed IoU column for the CE sets, so this "
          "application\n   has no independent cross-check of the kind that gates the map "
          "derivation. (2) K6b scores\n   `doe` on its own 4-D active subspace (B3), so "
          "the prevalence differs BY ARM within a cell\n   in 198 of 200 cells — the "
          "cross-arm ranking is NOT like-for-like, and `doe`'s slice is\n   the easier "
          "one, so the bias runs in its favour.\n")
    ce_out = {"provenance": _provenance(),
              "amendment": "F2a extended to CE_alpha; approved as a separate file, never "
                           "an overwrite",
              "source": ["results/k6b-conservative.json",
                         "results/k6b-conservative-spread.json"],
              "rows": len(k6b_rows),
              "gate": {"committed_iou_column_for_CE": None,
                       "falsifiable_check": "ce_vol*(1-ce_false_in) <= prevalence, else "
                                            "type II goes negative",
                       "negative_type_II": 0},
              "like_for_like_across_arms": False,
              "not_like_for_like_reason": (
                  "Amendment B3 evaluates `doe` on its 4-D active subspace (§2.8), so the "
                  "prevalence differs by arm in 198 of 200 cells and `doe`'s slice is "
                  "easier. Contrast the K6 map, where all eight arms share the 6-D grid "
                  "and the ranking IS like-for-like."),
              "cells": []}
    neg = 0
    print(f"   {'tau_f':>6}{'alpha':>7}  {'total error volume, best (lowest) first':<64}"
          f"{'empty':>7}{'sep':>10}")
    print(f"   {'':13}  `sep` = max |total - prevalence|. At sep = 0 every arm certifies "
          f"nothing and the\n   {'':13}  ranking is a ranking of PREVALENCES, which under "
          f"B3 differ by arm.")
    for tf in k6b_cfg["tau_fracs"]:
        for al in k6b_cfg["alphas"]:
            sub = [r for r in k6b_rows if r["tau_frac"] == tf]
            e = ce_error_volumes(sub, al)
            neg += int((e["type_II"] < 0).sum())
            prev_by_arm = _arm_means(sub, e["prevalence"], k6b_arms)
            rec = {"tau_frac": tf, "alpha": al,
                   "empty_frac": float(np.mean(e["empty"])),
                   "prevalence_by_arm": prev_by_arm}
            for metric in VOLUME_METRICS:
                means = _arm_means(sub, e[metric], k6b_arms)
                rec[f"{metric}_vol"] = means
                rec[f"{metric}_rank"] = _rank(means, lower_is_better=True)
                rec[f"{metric}_degenerate"] = _degenerate(means)
            # When every arm certifies nothing, total error volume IS the prevalence and
            # the "ranking" ranks prevalences, not arms. Under B3 `doe`'s prevalence is
            # the higher one, so it places last mechanically. Same class of error as
            # "type I read alone ranks silence first" -- flagged, not ranked.
            sep = max(abs(rec["total_vol"][a] - prev_by_arm[a]) for a in k6b_arms)
            rec["separation_from_prevalence"] = float(sep)
            rec["ranking_is_prevalence_only"] = bool(sep <= 1e-12)
            ce_out["cells"].append(rec)
            flag = ("  <<< PREVALENCE ONLY, not a statement about the arms"
                    if rec["ranking_is_prevalence_only"] else "")
            print(f"   {tf:>6.2f}{al:>7.2f}  {' < '.join(rec['total_rank']):<64}"
                  f"{rec['empty_frac']:>6.0%}{sep:>10.1e}{flag}")
    ce_out["gate"]["negative_type_II"] = neg
    print(f"\n   negative type-II volumes across all {len(k6b_rows)} rows x 3 alphas: "
          f"{neg}")
    informative = [c for c in ce_out["cells"] if not c["ranking_is_prevalence_only"]]
    ce_out["informative_cells"] = len(informative)
    doe_rank = [(c["tau_frac"], c["alpha"], c["total_rank"].index("doe") + 1)
                for c in informative if "doe" in c["total_rank"]]
    ce_out["doe_rank_on_total_error_volume_informative_cells"] = doe_rank
    print(f"\n   {len(informative)} of {len(ce_out['cells'])} cells carry any information "
          f"about the arms; {len(ce_out['cells']) - len(informative)} rank prevalence only.")
    print(f"   `doe` on total error volume in the informative cells (1 = best): "
          f"{[r for _, _, r in doe_rank]}")
    print("   Best of eight at every `tau_frac = 0.60` cell, worst of eight at every "
          "other — but read\n   WITH limit (2): `doe`'s prevalence is not the other "
          "arms' prevalence, and its slice is easier.")
    OUT_CE.write_text(json.dumps(ce_out, indent=1))
    print(f"\n  written to {OUT_CE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
