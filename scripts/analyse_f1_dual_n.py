"""Amendment F1 / F4 — every reported contrast at BOTH units, and containment un-pooled.

    .venv/bin/python scripts/analyse_f1_dual_n.py

Reads the committed result blobs through `git show HEAD:<path>`; writes
`results/f1-dual-n.json`. No campaign is run and nothing is re-simulated: every number
here comes from a JSON that was already on disk.

WHY THIS EXISTS
---------------
The project states its unit of analysis twice, differently.

* `docs/K6-TECHNICAL-REPORT.md` §3.8 — *"the `(instance, seed)` pair. 25 instances x 2
  seeds = n = 50 for every contrast."*
* `docs/RESEARCH-SUMMARY.md` §… — *"The two random seeds per landscape are averaged
  first; the test then uses the n = 25 paired differences (one number per landscape)."*

Two seeds on one landscape **share the landscape**. They are not independent units, so
n = 50 counts a shared unit twice: it narrows every bootstrap interval and lowers every
Wilcoxon p. The earlier paper chose the conservative version; K6 chose the other, and
nothing in the repository records the switch. AMENDMENT F1 (commit 07e98df) requires both,
with the n = 25 verdict governing:

* significant under **both** -> reported as it stands, with the n = 25 p quoted;
* significant at n = 50 and **not** at n = 25 -> **downgraded to n = 25's verdict**, with
  n = 50 printed beside it and labelled the anti-conservative unit. Never quoted alone.

THE ONE JUDGEMENT CALL THE AMENDMENT DID NOT SPECIFY, STATED SO IT CAN BE OVERRULED
-----------------------------------------------------------------------------------
"Seeds averaged first" is unambiguous when nothing is missing. It is not when a metric
carries `nan` (an empty region, an unscorable campaign). Averaging each arm over whatever
seeds it happens to have would compare arm A's two campaigns against arm B's one. So the
order used here is: **drop the `(instance, seed)` pair if either arm is `nan` — exactly as
n = 50 does — then average the surviving seeds within an instance, then pair instances.**
The n = 25 analysis therefore runs on a strict subset of the campaigns n = 50 admits, and
the two units differ *only* in aggregation, which is the thing F1 is trying to isolate.
Recorded in the output as `seed_average_policy`.

F4 — THE POOLED CONTAINMENT FIGURE IS WITHDRAWN, NOT WIDENED
------------------------------------------------------------
§3.7 pooled empirical containment over `tau_frac` to n <= 200 per (arm, alpha). The four
thresholds are computed on the same campaign, the same posterior and the same 512 draws;
they are not four Bernoulli trials. This script emits **per-cell** containment only, at
both units, each with its own `n`. It deliberately does not emit a pooled number, and it
must not be extended to.
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
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "f1-dual-n.json"

#: The two units. `INSTANCE_SEED` is §3.8's; `INSTANCE` is RESEARCH-SUMMARY's, and the
#: one the registered decision rule quotes.
INSTANCE_SEED = "instance_seed"
INSTANCE = "instance"

N_BOOT = 4000
BOOT_SEED = 0
SESOI = 0.02
ALPHA = 0.05

#: The A1 map cell `analyse_k6.py` names explicitly.
A1_GAMMA, A1_TAU_FRAC = 0.90, 0.75

#: §1.4 of the technical report, which is the authority. A **validated** metric is scored
#: against the noiseless oracle; a **model-internal** one is a functional of the fitted
#: posterior and nothing else, so a model that is confidently wrong scores well on it.
#: This matters to F1 specifically: a contrast that gains significance at the conservative
#: unit gains it as *whatever kind of evidence its metric was already*. A stronger reading
#: of `alpha*` is a stronger reading of a statistic under suspicion (§1.4 consequence 1),
#: not evidence that an arm certifies better.
VALIDATED = "validated"
MODEL_INTERNAL = "model-internal"
#: (prefix, class, higher_is_better). The direction is not decoration: `alpha*` is
#: higher-is-better and Brier is lower-is-better, so `versionb - versionb_random` reading
#: +0.0261 on one and -0.0071 on the other means BOTH favour `versionb`. Comparing raw
#: signs calls that a disagreement and inverts the conclusion, which is exactly what the
#: first cut of the corroboration audit below did.
METRIC_PREFIXES = (
    ("alpha_star", MODEL_INTERNAL, True),
    ("vorobev_deviation", MODEL_INTERNAL, False),
    ("vorobev_dev", MODEL_INTERNAL, False),
    ("regret", VALIDATED, False),
    ("auc", VALIDATED, True),
    ("brier", VALIDATED, False),
    ("iou", VALIDATED, True),
    ("ce_empirical", VALIDATED, True),
)


def _lookup(key: str):
    for prefix, kind, higher in METRIC_PREFIXES:
        if key == prefix or key.startswith(prefix + "_"):
            return prefix, kind, higher
    raise ValueError(f"metric {key!r} is not classified in §1.4 — classify it in "
                     "METRIC_PREFIXES before using it in a contrast")


def metric_class(key: str) -> str:
    """`VALIDATED` or `MODEL_INTERNAL` for a committed column name.

    Unclassified columns raise. The grid is about to triple across five families and two
    noise levels; a new column must be placed on one side of §1.4's table deliberately,
    not default to whichever side happens to be convenient.
    """
    return _lookup(key)[1]


def benefit_sign(key: str, mean: float) -> int:
    """+1 if a paired difference of `mean` on `key` favours the FIRST arm, -1 if the
    second, 0 for an exact tie. Direction-aware, so lower-is-better metrics compare
    correctly against higher-is-better ones."""
    if mean == 0 or not np.isfinite(mean):
        return 0
    higher = _lookup(key)[2]
    return int(np.sign(mean)) if higher else -int(np.sign(mean))

# Every other grid coordinate is READ FROM THE COMMITTED CONFIG, never hardcoded. A
# hardcoded `gammas` here silently dropped 0.70 and 0.80 and turned the 24-cell headline
# into a 16-cell one; the grid is about to triple across five families and two noise
# levels, and this is exactly the failure that would survive that unnoticed.


# --------------------------------------------------------------------------- committed
def committed(path: str) -> dict:
    """Read a blob at HEAD rather than from the working tree.

    Six agents are writing into `results/` concurrently; a previous worker compared
    against a file another process had already replaced.
    """
    blob = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout
    return json.loads(blob)


# ------------------------------------------------------------------------- statistics
def _by_campaign(rows, arm, key, filters):
    return {(r["instance"], r["seed"]): r[key] for r in rows
            if r["arm"] == arm and all(r[k] == v for k, v in filters.items())}


def paired(rows, arm_a, arm_b, key, unit, key_b=None, **filters):
    """Paired vectors for two arms at `unit`. Returns (a, b, dropped).

    `key_b` lets an arm be paired against itself on a second column, which is how the
    rule-P / rule-A contrast is expressed.
    """
    a = _by_campaign(rows, arm_a, key, filters)
    b = _by_campaign(rows, arm_b, key_b or key, filters)
    keys = sorted(set(a) & set(b))
    pa = np.array([a[k] for k in keys], dtype=float)
    pb = np.array([b[k] for k in keys], dtype=float)
    ok = ~(np.isnan(pa) | np.isnan(pb))
    dropped = int((~ok).sum())
    if unit == INSTANCE_SEED:
        return pa[ok], pb[ok], dropped
    if unit != INSTANCE:
        raise ValueError(f"unknown unit {unit!r}")
    # Seeds averaged first, over the pairs that survived the pairwise nan drop.
    acc: dict[str, list[tuple[float, float]]] = {}
    for (inst, _seed), va, vb, good in zip([k for k in keys], pa, pb, ok, strict=True):
        if good:
            acc.setdefault(inst, []).append((va, vb))
    insts = sorted(acc)
    ia = np.array([np.mean([x for x, _ in acc[i]]) for i in insts], dtype=float)
    ib = np.array([np.mean([y for _, y in acc[i]]) for i in insts], dtype=float)
    return ia, ib, dropped


def unpaired_icc(rows, arm, key, **filters) -> float:
    """Intra-class correlation of RAW per-arm values — NOT of paired differences.

    Same identity, different input: `1 + ICC = (n50/n25) * s25^2 / s50^2`, where `s25` is
    the variance of the 25 instance means and `s50` that of the 50 campaign values.

    **This is the portable half of F1.** The paired differences have a median ICC near
    zero, because pairing has already removed the landscape — the shared landscape effect
    cancels in the difference, which is exactly what makes pairing worth doing. That does
    **not** transfer to unpaired quantities. An arm mean, a containment proportion or a
    prevalence figure keeps the landscape effect in full, so for those the unit of
    analysis still matters and `n = 25` remains the default.
    """
    acc: dict[str, list[float]] = {}
    for r in rows:
        if r["arm"] == arm and all(r[k] == v for k, v in filters.items()):
            val = float(r[key])
            if np.isfinite(val):
                acc.setdefault(r["instance"], []).append(val)
    flat = np.array([x for v in acc.values() for x in v], dtype=float)
    means = np.array([np.mean(v) for v in acc.values()], dtype=float)
    if flat.size == 0 or means.size == 0 or flat.var() == 0:
        return float("nan")
    return float((flat.size / means.size) * means.var() / flat.var() - 1.0)


def contrast(pa, pb) -> dict:
    """Mean of `pa - pb`, its percentile bootstrap CI, and the two-sided Wilcoxon p.

    Identical mechanics to `analyse_k6.py::_contrast` and `analyse_fix1.py::_contrast`,
    including the resampling loop, so the n = 50 column reproduces them exactly. Changing
    the loop to a vectorised draw would change the random stream and silently move every
    committed interval.
    """
    if len(pa) < 3:
        return {"n": len(pa), "mean": float("nan"), "lo": float("nan"),
                "hi": float("nan"), "wilcoxon_p": float("nan"),
                "ci_excludes_zero": False, "above_sesoi": False, "status": "unscorable"}
    d = np.asarray(pa, dtype=float) - np.asarray(pb, dtype=float)
    rng = np.random.default_rng(BOOT_SEED)
    boots = [rng.choice(d, len(d), replace=True).mean() for _ in range(N_BOOT)]
    try:
        p = float(wilcoxon(pa, pb).pvalue)
    except ValueError:                       # every difference identically zero
        p = 1.0
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    return {"n": len(d), "mean": float(d.mean()), "lo": lo, "hi": hi, "wilcoxon_p": p,
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "above_sesoi": bool(abs(float(d.mean())) >= SESOI),
            "status": "significant" if p < ALPHA else "null"}


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down, adjusted p in the original order (Q39).

    Holm holds under arbitrary dependence, which is why it is valid across cells that
    share campaigns; it is conservative there, which is the right direction to err.
    """
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def dual_contrast(rows, arm_a, arm_b, key, key_b=None, **filters) -> dict:
    """The same contrast at both units, with the registered decision rule attached.

    Also carries `ci_inflation` — HOW anti-conservative n = 50 is on this contrast, as a
    number rather than as the amendment's assumed "roughly sqrt(2)". The exact sample
    identity is

        Var_boot(n=25) / Var_boot(n=50) = (n50/n25) * s25^2 / s50^2 = 1 + ICC

    where `s25` is the variance of the instance-mean differences and `s50` that of the
    campaign differences. sqrt(2) is the ICC = 1 corner — two seeds on a landscape
    agreeing perfectly. The ratio can equally land **below 1**, whenever two seeds on one
    landscape disagree more than two landscapes do, and then n = 50 was not
    anti-conservative at all. Measured, not assumed: that is the whole point of F1.
    """
    out, spread = {}, {}
    for tag, unit in (("n50", INSTANCE_SEED), ("n25", INSTANCE)):
        pa, pb, dropped = paired(rows, arm_a, arm_b, key, unit, key_b=key_b, **filters)
        c = contrast(pa, pb)
        c["dropped_nan"] = dropped
        out[tag] = c
        d = np.asarray(pa, dtype=float) - np.asarray(pb, dtype=float)
        spread[tag] = (float(d.var()), len(d))
    (v50, n50), (v25, n25) = spread["n50"], spread["n25"]
    if v50 > 0 and n25 > 0:
        out["ci_inflation"] = float(np.sqrt((n50 / n25) * v25 / v50))
        out["icc_equivalent"] = float(out["ci_inflation"] ** 2 - 1)
    else:
        out["ci_inflation"] = out["icc_equivalent"] = float("nan")
    out["status_n50"] = out["n50"]["status"]
    out["status_n25"] = out["n25"]["status"]
    out["status_changed"] = out["status_n50"] != out["status_n25"]
    for tag in ("n50", "n25"):
        out[f"bootstrap_wilcoxon_disagree_{tag}"] = bool(
            out[tag]["ci_excludes_zero"] != (out[tag]["status"] == "significant"))
    out["reported_unit"] = INSTANCE
    out["n50_label"] = "anti-conservative unit"
    out["metric"] = key
    out["metric_class"] = metric_class(key)
    out["arms"] = [arm_a, arm_b]
    out["key_b"] = key_b
    out["filters"] = dict(filters)
    return out


#: Validated columns to look for at the same cell when a model-internal contrast moves.
_COMPANION_STEMS = ("auc", "brier", "iou", "iou_vorobev_expectation", "regret")


def validated_companions(rows, key) -> list[str]:
    """Other validated columns available at the same cell as `key`, excluding `key`.

    `alpha_star_0.85` -> `auc_0.85`, `brier_0.85` in the Version B file. Used to ask
    whether a status change is corroborated by something else that consults the truth —
    for a model-internal metric that is the whole question, and for a validated one it is
    still worth knowing whether it stands alone.
    """
    if not rows:
        return []
    prefix = _lookup(key)[0]
    suffix = key[len(prefix):]
    have, seen, out = set(rows[0]), set(), []
    for cand in [st + suffix for st in _COMPANION_STEMS] + list(_COMPANION_STEMS):
        if cand in have and cand not in seen and cand != key:
            seen.add(cand)
            out.append(cand)
    return out


def containment(rows, key, unit) -> dict:
    """Empirical containment as a fraction of campaigns, at one unit and ONE cell.

    Empty certified sets return `None` and are dropped -- never counted as successes,
    since an empty set is vacuously contained and 52%-94% of them are empty. At the
    instance unit the two seeds of an instance are averaged first, so an instance
    contributes 0, 0.5 or 1; an instance with no scorable seed drops entirely.

    Deliberately per-cell. F4 withdrew the tau_frac-pooled form and this function has no
    way to express it.
    """
    def val(r):
        v = r.get(key)
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return float(bool(v))

    if unit == INSTANCE_SEED:
        vals = [val(r) for r in rows]
        vals = [v for v in vals if v is not None]
        return {"value": float(np.mean(vals)) if vals else None, "n": len(vals)}
    if unit != INSTANCE:
        raise ValueError(f"unknown unit {unit!r}")
    acc: dict[str, list[float]] = {}
    for r in rows:
        v = val(r)
        if v is not None:
            acc.setdefault(r["instance"], []).append(v)
    if not acc:
        return {"value": None, "n": 0}
    per_inst = [float(np.mean(v)) for v in acc.values()]
    return {"value": float(np.mean(per_inst)), "n": len(per_inst)}


# ------------------------------------------------------------------------------ family
def family(name, source, note, contrasts) -> dict:
    """A Holm family. Adjusted across its own cells at each unit independently."""
    for tag in ("n50", "n25"):
        raw = [c[tag]["wilcoxon_p"] for c in contrasts]
        finite = [p if np.isfinite(p) else 1.0 for p in raw]
        for c, p in zip(contrasts, holm(finite), strict=True):
            c[f"p_holm_{tag}"] = float(p)
            c[f"status_holm_{tag}"] = "significant" if p < ALPHA else "null"
    for c in contrasts:
        c["status_holm_changed"] = c["status_holm_n50"] != c["status_holm_n25"]
        c["family"] = name
        c["source"] = source
    return {"name": name, "source": source, "note": note,
            "holm_family_size": len(contrasts), "contrasts": contrasts}


def _label(**kw) -> str:
    return " ".join(f"{k}={v}" for k, v in kw.items())


def _print_family(f) -> None:
    print(f"\n{'=' * 118}\n{f['name']}   [{f['source']}]  Holm family of "
          f"{f['holm_family_size']}\n  {f['note']}\n{'=' * 118}")
    print(f"  {'contrast':<44}{'n50 mean':>10}{'n50 p':>10}{'n50 Holm':>10}"
          f"{'n25 mean':>10}{'n25 p':>10}{'n25 Holm':>10}  verdict")
    for c in f["contrasts"]:
        a, b = c["n50"], c["n25"]
        if c["status_holm_n50"] == "significant" and c["status_holm_n25"] == "significant":
            verdict = "holds at n=25"
        elif c["status_holm_n50"] == "significant":
            verdict = "*** DOWNGRADED ***"
        elif c["status_holm_n25"] == "significant":
            verdict = "gained at n=25"
        else:
            verdict = "null in both"
        print(f"  {c['label']:<44}{a['mean']:>+10.4f}{a['wilcoxon_p']:>10.2e}"
              f"{c['p_holm_n50']:>10.2e}{b['mean']:>+10.4f}{b['wilcoxon_p']:>10.2e}"
              f"{c['p_holm_n25']:>10.2e}  {verdict}")


# -------------------------------------------------------------------------------- main
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
    k6 = committed("results/k6-designspace.json")
    k6s = committed("results/k6-designspace-spread.json")
    k6_rows = k6["rows"] + k6s["rows"]
    k6b = committed("results/k6b-conservative.json")
    k6bs = committed("results/k6b-conservative-spread.json")
    k6b_rows = k6b["rows"] + k6bs["rows"]
    vb = committed("results/versionb.json")
    vb_rows = vb["rows"]
    fix1_rows = committed("results/fix1-terminal-rule.json")["rows"]

    # The spread arms were run separately and are merged here. Assert config agreement
    # first, exactly as `analyse_k6.py` does -- merging two grids would be silent.
    for base, extra, keys in (
            (k6, k6s, ("dim", "sigma", "gammas", "tau_fracs", "grid_n", "grid_seed")),
            (k6b, k6bs, ("dim", "sigma", "tau_fracs", "alphas", "subset_n", "n_draws",
                         "grid_seed"))):
        for k in keys:
            assert extra["config"][k] == base["config"][k], f"spread run disagrees on {k!r}"

    gammas = list(k6["config"]["gammas"])
    tau_fracs = list(k6["config"]["tau_fracs"])
    primary_gamma, primary_tau_frac = gammas[0], tau_fracs[0]
    k6b_tfs = list(k6b["config"]["tau_fracs"])
    k6b_alphas = list(k6b["config"]["alphas"])
    vb_tfs = list(vb["config"]["tau_fracs"])
    vb_alphas = list(vb["config"]["alphas"])
    assert (A1_GAMMA in gammas and A1_TAU_FRAC in tau_fracs), "A1 cell is off the grid"

    print(f"{'=' * 118}\nAMENDMENT F1 — every reported contrast at n = 50 "
          f"(instance, seed) AND n = 25 (instance, seeds averaged first)\n{'=' * 118}")
    print(f"  bootstrap {N_BOOT} resamples at default_rng({BOOT_SEED}); Wilcoxon "
          f"two-sided; Holm within each family; SESOI {SESOI}; alpha {ALPHA}")
    print("  Wilcoxon governs yes/no. The bootstrap reports magnitude. Disagreements "
          "between them are\n  reported, not resolved — and there are now four cells of "
          "them (2 statistics x 2 units).")

    fams = []

    # -- §5.1 paired regret contrasts ------------------------------------------------
    cs = []
    for a, b in [("lhs", "doe"), ("lhs", "qlogei"), ("lhs", "qlognei"),
                 ("doe", "qlogei"), ("doe", "qlognei"), ("sobol", "lhs"),
                 ("random", "lhs")]:
        c = dual_contrast(k6_rows, a, b, "regret",
                          gamma=primary_gamma, tau_frac=primary_tau_frac)
        c["label"] = f"{a} - {b}"
        cs.append(c)
    fams.append(family("§5.1 paired regret contrasts", "k6-designspace(+spread)",
                       "positive = the first arm has WORSE regret", cs))

    # -- §5.3 THE HEADLINE: screening isolated between two matched arms ---------------
    cs = []
    for g in gammas:
        for tf in tau_fracs:
            c = dual_contrast(k6_rows, "lhs", "doe", "auc_pred", gamma=g, tau_frac=tf)
            c["label"] = _label(gamma=g, tau_frac=tf)
            cs.append(c)
    fams.append(family("§5.3 HEADLINE 1 — `lhs` - `doe` on AUC(predictive), 24 cells",
                       "k6-designspace(+spread)",
                       "significant in 24 of 24 as reported; positive favours the "
                       "UNSCREENED arm", cs))

    # -- §5.2 / §5.4 spread vs clustered ---------------------------------------------
    cs = []
    for g in gammas:
        for tf in tau_fracs:
            c = dual_contrast(k6_rows, "doe", "qlogei", "auc_pred", gamma=g, tau_frac=tf)
            c["label"] = _label(gamma=g, tau_frac=tf)
            cs.append(c)
    fams.append(family("§5.4 `doe` - `qlogei` on AUC(predictive), 24 cells",
                       "k6-designspace(+spread)",
                       "reproduces `results/k6-analysis.json` `spread_vs_clustered` at "
                       "n = 50", cs))

    # -- §5.5 Amendment A1, the additive-kernel arms ---------------------------------
    cs = []
    for add in ("qlogei-add", "qlogei-addonly"):
        c = dual_contrast(k6_rows, add, "qlogei", "regret",
                          gamma=primary_gamma, tau_frac=primary_tau_frac)
        c["label"] = f"{add} - qlogei regret"
        cs.append(c)
        c = dual_contrast(k6_rows, add, "qlogei", "auc_pred",
                          gamma=A1_GAMMA, tau_frac=A1_TAU_FRAC)
        c["label"] = f"{add} - qlogei AUC g={A1_GAMMA} tf={A1_TAU_FRAC}"
        cs.append(c)
    fams.append(family("§5.5 Amendment A1 — the additive kernel, regret and map",
                       "k6-designspace(+spread)",
                       "Q30 measured dregret 0.0015, p = 0.71; A1 asks the same question "
                       "on the map", cs))

    cs = []
    for add in ("qlogei-add", "qlogei-addonly"):
        for tf in k6b_tfs:
            c = dual_contrast(k6b_rows, add, "qlogei", "alpha_star", tau_frac=tf)
            c["label"] = f"{add} - qlogei alpha* tf={tf}"
            cs.append(c)
    fams.append(family("§5.5 Amendment A1 on `alpha*`, 8 contrasts", "k6b-conservative"
                       "(+spread)",
                       "the report's 'seven of eight have p >= 0.18; one at p = 0.0125, "
                       "adjusted 0.100'", cs))

    # -- §5.8 paired contrasts on alpha* ----------------------------------------------
    cs = []
    for a, b in [("doe", "qlogei"), ("doe", "qlognei"), ("lhs", "doe"),
                 ("lhs", "qlognei"), ("sobol", "qlognei"), ("sobol", "lhs"),
                 ("random", "lhs")]:
        for tf in k6b_tfs:
            c = dual_contrast(k6b_rows, a, b, "alpha_star", tau_frac=tf)
            c["label"] = f"{a} - {b} tf={tf}"
            cs.append(c)
    fams.append(family("§5.8 paired contrasts on `alpha*`, 7 pairs x 4 thresholds",
                       "k6b-conservative(+spread)",
                       "`alpha*` is quantised to multiples of 1/512 and heavily tied — "
                       "the regime where bootstrap and Wilcoxon come apart (§6.7)", cs))

    # -- §5.11.3 KILL 1 ----------------------------------------------------------------
    cs = []
    for metric in ("alpha_star", "auc"):
        for tf in vb_tfs:
            c = dual_contrast(vb_rows, "versionb", "qlognei", f"{metric}_{tf}")
            c["label"] = f"versionb - qlognei {metric} tf={tf}"
            cs.append(c)
    fams.append(family("§5.11.3 KILL 1 — does plate 2 close the gap to qLogNEI?",
                       "versionb", "positive favours versionb; family of 8 as reported",
                       cs))

    # -- §5.11.4 KILL 2 ----------------------------------------------------------------
    cs = []
    for metric in ("alpha_star", "auc"):
        for tf in vb_tfs:
            c = dual_contrast(vb_rows, "versionb", "versionb_random", f"{metric}_{tf}")
            c["label"] = f"versionb - versionb_random {metric} tf={tf}"
            cs.append(c)
    fams.append(family("§5.11.4 KILL 2 — does the LSE criterion beat 8 RANDOM wells?",
                       "versionb",
                       "the report's own Holm family of eight (smallest raw p = 0.0030 "
                       "-> 0.024)", cs))

    cs = []
    for tf in vb_tfs:
        c = dual_contrast(vb_rows, "versionb", "versionb_random", f"vorobev_dev_{tf}")
        c["label"] = f"versionb - versionb_random vorobev_dev tf={tf}"
        cs.append(c)
    fams.append(family("§5.11.4 Vorob'ev deviation, reported beside KILL 2", "versionb",
                       "MODEL-INTERNAL (§1.4) — lower means more certain, not more right",
                       cs))

    # -- §5.11.5 does a second plate help at all? -------------------------------------
    cs = []
    for metric in ("alpha_star", "auc"):
        for tf in vb_tfs:
            c = dual_contrast(vb_rows, "versionb", "plate1_only", f"{metric}_{tf}")
            c["label"] = f"versionb - plate1_only {metric} tf={tf}"
            cs.append(c)
    fams.append(family("§5.11.5 `versionb` - `plate1_only` — the second plate itself",
                       "versionb",
                       "the report: survives Holm across its own EIGHT tests at "
                       "tau_frac=0.60 on both AUC (+0.0328, adj 0.0240) and alpha* "
                       "(+0.0236, adj 0.0267)", cs))

    cs = [dict(dual_contrast(vb_rows, "versionb", "plate1_only", "regret"),
               label="versionb - plate1_only regret"),
          dict(dual_contrast(vb_rows, "versionb", "qlognei", "regret"),
               label="versionb - qlognei regret")]
    fams.append(family("§5.11.2 Version B regret contrasts", "versionb",
                       "positive = versionb WORSE; the report quotes +0.0276 p=0.0166 "
                       "and +0.0014 p=0.86", cs))

    # -- D20 / Fix 1: HEADLINE 2 -------------------------------------------------------
    fix1_arms = sorted({r["arm"] for r in fix1_rows},
                       key=lambda a: [r["arm"] for r in fix1_rows].index(a))
    cs = []
    for a in fix1_arms:
        c = dual_contrast(fix1_rows, a, a, "regret_p", key_b="regret_a")
        c["label"] = f"{a}: rule P - rule A"
        cs.append(c)
    fams.append(family("D20 HEADLINE 2 — the rule-P reversal, per arm",
                       "fix1-terminal-rule",
                       "NEGATIVE means the posterior-mean rule is BETTER; reproduces "
                       "`results/fix1-analysis.json` at n = 50", cs))

    # The reversal proper: the sign flip between the two rules, and the registered kill.
    cs = []
    for rule, key in (("rule A", "regret_a"), ("rule P", "regret_p")):
        c = dual_contrast(fix1_rows, "doe", "versionb", key)
        c["label"] = f"doe - versionb under {rule}"
        cs.append(c)
    fams.append(family("D20 HEADLINE 2 — the SIGN FLIP that is the reversal",
                       "fix1-terminal-rule",
                       "negative = `doe` ahead. Under rule A `doe` leads; under rule P "
                       "`versionb` does. Both signs must be established, not one.", cs))

    imp = {}
    for a in ("versionb", "doe"):
        pa, pb, _ = paired(fix1_rows, a, a, "regret_a", INSTANCE_SEED, key_b="regret_p")
        ia, ib, _ = paired(fix1_rows, a, a, "regret_a", INSTANCE, key_b="regret_p")
        imp[a] = {"n50": pa - pb, "n25": ia - ib}
    kill = {}
    for tag in ("n50", "n25"):
        c = contrast(imp["versionb"][tag], imp["doe"][tag])
        c["fired"] = not (c["mean"] >= SESOI and c["wilcoxon_p"] < ALPHA)
        kill[tag] = c
    kill["status_changed"] = kill["n50"]["status"] != kill["n25"]["status"]
    kill["contrast"] = "improvement(versionb) - improvement(doe)"
    kill["note"] = ("registered OUTSIDE the per-arm Holm family so it is not corrected "
                    "twice; improvement = regret_A - regret_P")

    # -- F4: per-cell empirical containment, at both units -----------------------------
    print(f"\n{'=' * 118}\nF4 — EMPIRICAL CONTAINMENT, PER CELL ONLY. The pooled figure "
          f"is WITHDRAWN.\n{'=' * 118}")
    print("  Four thresholds on the same campaign, the same posterior and the same 512 "
          "draws are not\n  four Bernoulli trials. Each row below states its own cell and "
          "its own n.\n")
    contain = {"k6b": [], "versionb": []}
    k6b_arms = sorted({r["arm"] for r in k6b_rows})
    print(f"  {'source':<10}{'arm':<17}{'tau_f':>6}{'alpha':>7}"
          f"{'n=50':>10}{'n':>5}{'n=25':>10}{'n':>5}  verdict")
    for arm in k6b_arms:
        for tf in k6b_tfs:
            sub = [r for r in k6b_rows if r["arm"] == arm and r["tau_frac"] == tf]
            for al in k6b_alphas:
                c50 = containment(sub, f"ce_empirical_{al}", INSTANCE_SEED)
                c25 = containment(sub, f"ce_empirical_{al}", INSTANCE)
                rec = {"arm": arm, "tau_frac": tf, "alpha": al, "n50": c50, "n25": c25,
                       "empty_frac": float(np.mean([r[f"ce_empty_{al}"] for r in sub])),
                       "holds_n50": None if c50["value"] is None else bool(c50["value"] >= al),
                       "holds_n25": None if c25["value"] is None else bool(c25["value"] >= al)}
                rec["verdict_changed"] = rec["holds_n50"] != rec["holds_n25"]
                contain["k6b"].append(rec)
                if c50["value"] is None:
                    continue
                v = ("ok" if rec["holds_n50"] else "FAIL")
                v2 = ("ok" if rec["holds_n25"] else "FAIL")
                flag = "  <<< VERDICT CHANGES" if rec["verdict_changed"] else ""
                print(f"  {'k6b':<10}{arm:<17}{tf:>6.2f}{al:>7.2f}"
                      f"{c50['value']:>10.4f}{c50['n']:>5}{c25['value']:>10.4f}"
                      f"{c25['n']:>5}  {v}/{v2}{flag}")
    vb_arms = sorted({r["arm"] for r in vb_rows})
    for arm in vb_arms:
        sub = [r for r in vb_rows if r["arm"] == arm]
        for tf in vb_tfs:
            for al in vb_alphas:
                key = f"ce_empirical_{tf}_{al}"
                c50 = containment(sub, key, INSTANCE_SEED)
                c25 = containment(sub, key, INSTANCE)
                rec = {"arm": arm, "tau_frac": tf, "alpha": al, "n50": c50, "n25": c25,
                       "empty_frac": float(np.mean([r[f"ce_empty_{tf}_{al}"] for r in sub])),
                       "holds_n50": None if c50["value"] is None else bool(c50["value"] >= al),
                       "holds_n25": None if c25["value"] is None else bool(c25["value"] >= al)}
                rec["verdict_changed"] = rec["holds_n50"] != rec["holds_n25"]
                contain["versionb"].append(rec)
                if c50["value"] is None:
                    continue
                v = ("ok" if rec["holds_n50"] else "FAIL")
                v2 = ("ok" if rec["holds_n25"] else "FAIL")
                flag = "  <<< VERDICT CHANGES" if rec["verdict_changed"] else ""
                print(f"  {'versionb':<10}{arm:<17}{tf:>6.2f}{al:>7.2f}"
                      f"{c50['value']:>10.4f}{c50['n']:>5}{c25['value']:>10.4f}"
                      f"{c25['n']:>5}  {v}/{v2}{flag}")

    for f in fams:
        _print_family(f)

    print(f"\n{'=' * 118}\n  THE REGISTERED KILL (outside the Holm family)\n{'=' * 118}")
    for tag in ("n50", "n25"):
        c = kill[tag]
        print(f"    {tag}: {c['mean']:+.4f} [{c['lo']:+.4f},{c['hi']:+.4f}] "
              f"p={c['wilcoxon_p']:.3e} n={c['n']}  "
              f"KILL {'FIRED' if c['fired'] else 'DID NOT FIRE'}")

    # -- the audit the review asked for: WHAT KIND of evidence changed? ----------------
    # A status change on `alpha*` and one on AUC are not the same finding. `alpha*` and
    # Vorob'ev deviation are functionals of the fitted posterior and nothing else (§1.4),
    # and this project's own worked example is `doe`: `grid_r2` = -6.19 and it still
    # scores the `alpha*` ceiling of 1.0000. So a contrast that gains significance at the
    # conservative unit gains it as whatever kind of evidence its metric already was, and
    # a model-internal gain is a stronger reading of a statistic under suspicion.
    ROWSETS = {"k6-designspace(+spread)": k6_rows,
               "k6b-conservative(+spread)": k6b_rows,
               "versionb": vb_rows,
               "fix1-terminal-rule": fix1_rows}
    all_cs = [c for f in fams for c in f["contrasts"]]
    audit = []
    for c in all_cs:
        if not c["status_holm_changed"]:
            continue
        direction = ("upgraded" if c["status_holm_n25"] == "significant"
                     else "downgraded")
        rec = {"family": c["family"], "label": c["label"], "metric": c["metric"],
               "metric_class": c["metric_class"], "direction": direction,
               "mean": c["n25"]["mean"], "above_sesoi": c["n25"]["above_sesoi"],
               "p_holm_n50": c["p_holm_n50"], "p_holm_n25": c["p_holm_n25"],
               "ci_inflation": c["ci_inflation"],
               "quotable_as": ("evidence about the map" if c["metric_class"] == VALIDATED
                               else "a stronger reading of a MODEL-INTERNAL statistic; "
                                    "NOT evidence that the arm certifies better (§1.4 "
                                    "consequence 1)"),
               "corroboration": []}
        rows = ROWSETS[c["source"]]
        for comp in validated_companions(rows, c["metric"]):
            cc = dual_contrast(rows, c["arms"][0], c["arms"][1], comp,
                               key_b=c["key_b"], **c["filters"])
            rec["corroboration"].append({
                "metric": comp, "metric_class": cc["metric_class"],
                "n50": cc["n50"], "n25": cc["n25"],
                "agrees_in_benefit_direction": bool(
                    benefit_sign(comp, cc["n25"]["mean"])
                    == benefit_sign(c["metric"], c["n25"]["mean"])),
                "significant_n25_raw": cc["status_n25"] == "significant"})
        agree = [x for x in rec["corroboration"] if x["agrees_in_benefit_direction"]]
        rec["corroborated"] = bool(agree) and any(
            x["significant_n25_raw"] for x in agree) and not any(
            x["significant_n25_raw"] and not x["agrees_in_benefit_direction"]
            for x in rec["corroboration"])
        audit.append(rec)

    print(f"\n{'=' * 118}\n  WHAT KIND OF EVIDENCE MOVED? Every Holm status change, "
          f"classified by §1.4\n{'=' * 118}")
    print("  A gain on `alpha*` is a stronger reading of a posterior functional, not of "
          "the map. Where a\n  model-internal contrast moved, the same arm pair is "
          "re-run at the same cell on every\n  VALIDATED column the file carries.\n")
    for r in audit:
        print(f"  [{r['direction'].upper()}] {r['label']}  ({r['metric']} — "
              f"{r['metric_class']})")
        print(f"      Holm {r['p_holm_n50']:.3e} -> {r['p_holm_n25']:.3e};  "
              f"mean {r['mean']:+.4f}; SESOI {'cleared' if r['above_sesoi'] else 'NOT met'}"
              f"; inflation {r['ci_inflation']:.3f}")
        if r["metric_class"] != VALIDATED:
            print(f"      >>> {r['quotable_as']}")
        for x in r["corroboration"]:
            print(f"      corroborate on {x['metric']:<24} n25 "
                  f"{x['n25']['mean']:+.4f} p={x['n25']['wilcoxon_p']:.4f}  "
                  f"agrees={x['agrees_in_benefit_direction']!s:<5} "
                  f"sig(raw)={x['significant_n25_raw']}")
        if not r["corroboration"] and r["metric_class"] != VALIDATED:
            print("      corroborate: NO validated column at this cell in this file")
        elif r["corroboration"]:
            print(f"      => CORROBORATED BY A VALIDATED METRIC: {r['corroborated']}")

    # -- the count the registration asks for ------------------------------------------
    raw_changed = [c for c in all_cs if c["status_changed"]]
    holm_changed = [c for c in all_cs if c["status_holm_changed"]]
    downgraded = [c for c in all_cs
                  if c["status_holm_n50"] == "significant"
                  and c["status_holm_n25"] != "significant"]
    upgraded = [c for c in all_cs
                if c["status_holm_n50"] != "significant"
                and c["status_holm_n25"] == "significant"]
    contain_changed = [r for v in contain.values() for r in v
                       if r["verdict_changed"] and r["n50"]["value"] is not None]

    # The portable half: the same statistic on RAW values, where the landscape does NOT
    # cancel. Reported so the near-zero paired ICC is not mis-generalised to arm means,
    # containment proportions or prevalence figures.
    unpaired = {}
    for arm in sorted({r["arm"] for r in k6_rows}):
        vals = [unpaired_icc(k6_rows, arm, "auc_pred", gamma=g, tau_frac=tf)
                for g in gammas for tf in tau_fracs]
        vals = [v for v in vals if np.isfinite(v)]
        if vals:
            unpaired[arm] = {"median": float(np.median(vals)),
                             "min": float(np.min(vals)), "max": float(np.max(vals)),
                             "cells": len(vals)}
    print(f"\n{'=' * 118}\n  THE PORTABLE HALF — the near-zero ICC is a property of "
          f"PAIRED DIFFERENCES, not of this design\n{'=' * 118}")
    print("  Pairing removes the landscape: the shared landscape effect cancels in the "
          "difference, which\n  is what makes pairing worth doing. Raw per-arm values "
          "keep it in full. So for anything\n  UNPAIRED — arm means with intervals, "
          "containment proportions, prevalence — the unit still\n  matters and n = 25 "
          "stays the default.\n")
    print(f"  {'arm':<17}{'unpaired ICC of raw auc_pred (median)':>38}{'min':>9}{'max':>9}")
    for arm, v in sorted(unpaired.items(), key=lambda kv: -kv[1]["median"]):
        print(f"  {arm:<17}{v['median']:>+38.3f}{v['min']:>+9.3f}{v['max']:>+9.3f}")

    infl = np.array([c["ci_inflation"] for c in all_cs
                     if np.isfinite(c["ci_inflation"])])
    summary = {
        "total_contrasts": len(all_cs),
        "ci_inflation": {
            "definition": ("sqrt(Var_boot(n=25)/Var_boot(n=50)) = sqrt(1 + ICC) of the "
                           "paired differences. F1 assumed 'roughly sqrt(2)' = 1.414, "
                           "which is the ICC = 1 corner."),
            "n": int(infl.size), "median": float(np.median(infl)),
            "min": float(infl.min()), "max": float(infl.max()),
            "below_one": int((infl < 1.0).sum()),
            "reading": ("n = 50 is anti-conservative by this factor and no more. Where "
                        "it is at or below 1, the two seeds of a landscape disagree at "
                        "least as much as two landscapes do, and n = 50 was not "
                        "anti-conservative on that contrast at all.")},
        "status_changed_raw_wilcoxon": len(raw_changed),
        "status_changed_holm": len(holm_changed),
        "downgraded_holm": [f"{c['family']}: {c['label']}" for c in downgraded],
        "upgraded_holm": [f"{c['family']}: {c['label']}" for c in upgraded],
        "unpaired_icc_raw_auc_pred": unpaired,
        "unpaired_icc_reading": (
            "The near-zero ICC of the PAIRED DIFFERENCES is a property of pairing, not "
            "of this design: the landscape cancels in a difference. Raw per-arm values "
            "keep it, and the unpaired ICC is both large and arm-dependent. For any "
            "UNPAIRED quantity -- arm means with intervals, containment proportions, "
            "prevalence -- the unit of analysis still matters and n=25 stays the "
            "default. This is the portable half of F1."),
        "containment_cells": sum(len(v) for v in contain.values()),
        "containment_verdict_changed": len(contain_changed),
        "status_changes_by_metric_class": {
            k: sum(1 for r in audit if r["metric_class"] == k)
            for k in (VALIDATED, MODEL_INTERNAL)},
    }
    print(f"\n{'=' * 118}\n  HOW MANY REPORTED CONTRASTS CHANGE STATUS AT n = 25?"
          f"\n{'=' * 118}")
    print(f"    contrasts recomputed          : {summary['total_contrasts']}")
    print(f"    CI inflation sqrt(1+ICC)      : median {np.median(infl):.4f}  range "
          f"[{infl.min():.4f}, {infl.max():.4f}]  ({int((infl < 1.0).sum())} below 1.0)")
    print("      F1 assumed 'roughly sqrt(2)' = 1.4142. That is the ICC = 1 corner. "
          "MEASURED, it is not that.")
    print(f"    status changes, raw Wilcoxon  : {summary['status_changed_raw_wilcoxon']}")
    print(f"    status changes, Holm-adjusted : {summary['status_changed_holm']}")
    print(f"      of which DOWNGRADED (sig at n=50, not at n=25): {len(downgraded)}")
    for c in downgraded:
        print(f"        - {c['family']}: {c['label']}  "
              f"(n50 Holm {c['p_holm_n50']:.3e} -> n25 Holm {c['p_holm_n25']:.3e})")
    print(f"      of which gained significance at n=25          : {len(upgraded)}")
    for c in upgraded:
        print(f"        + {c['family']}: {c['label']}  "
              f"(n50 Holm {c['p_holm_n50']:.3e} -> n25 Holm {c['p_holm_n25']:.3e})")
    print(f"    containment cells             : {summary['containment_cells']}"
          f" · verdict changes: {len(contain_changed)}")

    OUT.write_text(json.dumps({
        "provenance": _provenance(),
        "amendment": "F1 (both units) and F4 (containment un-pooled), commit 07e98df",
        "units": {"n50": "(instance, seed) — docs/K6-TECHNICAL-REPORT.md §3.8",
                  "n25": "instance, seeds averaged first — docs/RESEARCH-SUMMARY.md"},
        "seed_average_policy": (
            "drop the (instance, seed) pair if either arm is nan, exactly as n=50 does, "
            "THEN average surviving seeds within an instance, THEN pair instances. The "
            "n=25 set is a strict subset of what n=50 admits, so the two units differ "
            "only in aggregation. Not specified by the amendment; stated so it can be "
            "overruled."),
        "statistics": {"n_boot": N_BOOT, "boot_seed": BOOT_SEED, "sesoi": SESOI,
                       "alpha": ALPHA,
                       "decision_rule": (
                           "Wilcoxon governs yes/no; the bootstrap reports magnitude; "
                           "disagreements are reported, not resolved. n=25 governs; n=50 "
                           "is labelled the anti-conservative unit and never quoted "
                           "alone.")},
        "summary": summary,
        "families": fams,
        "status_change_audit": audit,
        "registered_kill": kill,
        "containment_per_cell": contain,
        "pooled_containment": ("WITHDRAWN per F4 — four thresholds on one campaign, one "
                               "posterior and one set of 512 draws are not four "
                               "Bernoulli trials. No pooled number is emitted."),
    }, indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
