"""Version C section 0 -- read the gate, apply the branch, validate the model.

    .venv/bin/python scripts/analyse_versionc_gate.py
    .venv/bin/python scripts/analyse_versionc_gate.py --also results/fix1-terminal-rule.json

Reads `results/versionc-gate-s010.json` and answers two separate questions.

**THE BRANCH.** Section 0's registered decision, on SPADE's own rule-P regret:

    regret_P <= 0.090   IDENTIFICATION_ARTEFACT   section 2 is NOT built
    regret_P >= 0.110   SEARCH_DEFICIT            trust region required
    between             INCONCLUSIVE              section 2 is built as an ARM

The branch function is **imported from the runner**, not restated, so the analysis cannot
drift from the file it analyses. It is applied to `versionb` by name: reading the best
arm's number instead would make the gate fire on whichever arm happened to win, which is
a different and much easier question.

**THE MODEL.** `regret_P ~ sigma / sqrt(n_eff)` is the reasoning behind section 2.2's
well-count formula `n_required = (sigma_hat / r*)^2`. If `R^2` is high and the slope is
near 1 that formula is validated. If not, **section 2.2 has no basis and must be replaced
by empirical calibration** -- which is a finding about section 2.2 whichever way the
branch above falls, and is the reason the regression is run even when the branch says not
to build section 2 at all.

Section 0 says "across all arms and **both** sigma". The gate run is sigma = 0.10 only, so
`both_sigma` is reported as a field rather than assumed: a one-sigma fit is a different
claim and must not be printed as if it were the registered one. `--also` accepts a second
results file (fix1-terminal-rule.json is the sigma = 0.25 rule-P run) and uses it wherever
it carries `n_eff`; it currently does not, so the two-sigma regression needs the gate
runner re-run at sigma = 0.25 and that gap is printed rather than papered over.

Statistics follow the Fix 1 registration exactly: unit of analysis `(instance, seed)`,
paired, 4,000-resample percentile bootstrap of the paired differences on
`default_rng(0)`, two-sided Wilcoxon, Holm across the arms, SESOI 0.02. Per Q20 section 2,
Wilcoxon governs yes/no and the bootstrap reports magnitude; **disagreements between them
are reported, not resolved.**
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_run_versionc_gate", ROOT / "scripts" / "run_versionc_gate.py")
_G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_G)

#: Imported, never restated. One definition of the branch, in the runner that registered it.
gate_branch = _G.gate_branch
GATE_FILE = _G.OUT
PRIMARY_ARM = "versionb"

SESOI, ALPHA = 0.02, 0.05
N_BOOT, BOOT_SEED = 4_000, 0


def _holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni, returned in the input order and enforced monotone."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, out, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        out[i] = running
    return out


def _contrast(a: np.ndarray, b: np.ndarray) -> dict:
    """Mean of ``a - b``, its percentile bootstrap CI, and the two-sided Wilcoxon p.

    The bootstrap resamples the **paired differences**, which is the unit of analysis.
    """
    d = a - b
    rng = np.random.default_rng(BOOT_SEED)
    boot = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(N_BOOT)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:            # every difference is exactly zero
        p = 1.0
    return {"mean": float(d.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "wilcoxon_p": p, "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "above_sesoi": bool(abs(float(d.mean())) >= SESOI), "n": int(d.size)}


def branch_for(rows: list[dict], arm: str = PRIMARY_ARM) -> dict:
    """Apply the registered branch to one named arm's mean rule-P regret."""
    vals = [float(r["regret_p"]) for r in rows if r["arm"] == arm]
    if not vals:
        raise ValueError(f"no rows for arm {arm!r}; the branch is undefined")
    mean = float(np.mean(vals))
    return {"arm": arm, "n": len(vals), "mean_regret_p": mean,
            "branch": gate_branch(mean),
            "thresholds": {"artefact_at_or_below": _G.BRANCH_ARTEFACT,
                           "deficit_at_or_above": _G.BRANCH_DEFICIT}}


def n_eff_regression(rows: list[dict]) -> dict:
    """OLS of ``regret_P`` on ``sigma / sqrt(n_eff)``. Slope, intercept, R^2.

    Reports a low ``R^2`` as a number rather than raising: the falsifying outcome is the
    informative one here, and an exception would make it invisible in the results file.
    """
    usable = [r for r in rows
              if r.get("n_eff") and np.isfinite(float(r.get("regret_p", np.nan)))]
    if len(usable) < 3:
        raise ValueError(f"need at least 3 usable rows to regress, got {len(usable)}")
    x = np.array([float(r.get("sigma_over_sqrt_n_eff",
                              float(r["sigma"]) / float(r["n_eff"]) ** 0.5))
                  for r in usable])
    y = np.array([float(r["regret_p"]) for r in usable])
    # RELATIVE, not `== 0.0`. A hundred copies of 0.07 do not sum to exactly 7.0 in
    # float64, so an exact test leaves std ~1e-18 and lets a poorly-conditioned polyfit
    # through -- measured, and it produced a confident slope of 0.688 on constant x.
    if float(x.std()) <= 1e-12 * max(abs(float(x.mean())), 1.0):
        # Every campaign landed on the same n_eff, so the slope is not identified. A
        # polyfit here returns a number the conditioning warning quietly disowns; the
        # honest answer is that this design cannot estimate the slope at all.
        return {"slope": float("nan"), "intercept": float(y.mean()), "r2": float("nan"),
                "n": len(usable),
                "sigmas": sorted({round(float(r["sigma"]), 10) for r in usable}),
                "both_sigma": len({round(float(r["sigma"]), 10) for r in usable}) >= 2,
                "slope_near_one": False,
                "note": "sigma/sqrt(n_eff) is constant across all rows; slope unidentified"}
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    sigmas = sorted({round(float(r["sigma"]), 10) for r in usable})
    return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2),
            "n": len(usable), "sigmas": sigmas, "both_sigma": len(sigmas) >= 2,
            "slope_near_one": bool(abs(float(slope) - 1.0) <= 0.25)}


def _load(path: Path) -> list[dict]:
    d = json.loads(Path(path).read_text())
    if isinstance(d, dict) and not d.get("complete", True):
        print(f"  ! {Path(path).name} is PARTIAL: "
              f"{d.get('keys_present')} of {d.get('keys_expected')} keys")
    return d if isinstance(d, list) else d.get("rows", d)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(GATE_FILE))
    ap.add_argument("--also", default=None,
                    help="a second results file for the two-sigma regression")
    args = ap.parse_args()

    rows = _load(Path(args.file))
    arms = sorted({r["arm"] for r in rows})
    print(f"Version C section 0 · {len(rows)} rows · {len(arms)} arms")
    print(f"  bootstrap {N_BOOT} resamples default_rng({BOOT_SEED}); Wilcoxon two-sided; "
          f"Holm across {len(arms)} arms; SESOI {SESOI}\n")

    # --- per-arm rule A vs rule P ------------------------------------------------------
    per_arm = []
    for arm in arms:
        sub = sorted([r for r in rows if r["arm"] == arm],
                     key=lambda r: (r["instance"], r["seed"]))
        a = np.array([float(r["regret_a"]) for r in sub])
        p = np.array([float(r["regret_p"]) for r in sub])
        per_arm.append({"arm": arm, "n": len(sub),
                        "mean_regret_a": float(a.mean()),
                        "mean_regret_p": float(p.mean()),
                        "mean_n_eff": float(np.mean([r["n_eff"] for r in sub])),
                        "improvement": _contrast(a, p)})
    for x, ph in zip(per_arm, _holm([x["improvement"]["wilcoxon_p"] for x in per_arm])):
        x["improvement"]["p_holm"] = float(ph)
        x["improvement"]["holm_significant"] = bool(ph < ALPHA)

    print(f"{'arm':<22}{'rule A':>9}{'rule P':>9}{'A-P':>9}{'95% CI':>21}"
          f"{'p Holm':>9}{'n_eff':>8}")
    for x in sorted(per_arm, key=lambda v: v["mean_regret_p"]):
        c = x["improvement"]
        ci = "[{:+.4f}, {:+.4f}]".format(c["ci_lo"], c["ci_hi"])
        print(f"{x['arm']:<22}{x['mean_regret_a']:>9.4f}{x['mean_regret_p']:>9.4f}"
              f"{c['mean']:>+9.4f}{ci:>21}"
              f"{c['p_holm']:>9.4f}{x['mean_n_eff']:>8.2f}")

    # --- the branch --------------------------------------------------------------------
    verdict = branch_for(rows)
    best = min(per_arm, key=lambda v: v["mean_regret_p"])
    print(f"\nBRANCH  {PRIMARY_ARM} mean rule-P regret {verdict['mean_regret_p']:.4f} "
          f"-> {verdict['branch']}")
    print(f"        best arm under rule P is {best['arm']} at "
          f"{best['mean_regret_p']:.4f}; gap "
          f"{verdict['mean_regret_p'] - best['mean_regret_p']:+.4f} "
          f"against SESOI {SESOI}")

    # --- the model ---------------------------------------------------------------------
    reg_rows = list(rows)
    if args.also:
        extra = _load(Path(args.also))
        with_neff = [r for r in extra if r.get("n_eff")]
        print(f"\n  --also {Path(args.also).name}: {len(extra)} rows, "
              f"{len(with_neff)} carry n_eff")
        reg_rows += with_neff
    fit = n_eff_regression(reg_rows)
    print(f"\nMODEL   regret_P ~ sigma/sqrt(n_eff): slope {fit['slope']:.4f} "
          f"intercept {fit['intercept']:+.4f} R2 {fit['r2']:.4f} (n={fit['n']})")
    print(f"        sigmas present {fit['sigmas']} · both_sigma={fit['both_sigma']}")
    if not fit["both_sigma"]:
        print("        ! ONE SIGMA ONLY. Section 0 registers the regression across BOTH. "
              "Re-run the gate runner at sigma=0.25 for the registered version; "
              "fix1-terminal-rule.json carries regret_p there but no n_eff.")
    if not (fit["slope_near_one"] and fit["r2"] > 0.5):
        print("        ! The sigma/sqrt(n_eff) model is NOT validated. Section 2.2's "
              "well-count formula has no basis and must be replaced by empirical "
              "calibration.")

    out = Path(args.file).with_name("versionc-gate-analysis.json")
    out.write_text(json.dumps({"source": str(args.file), "per_arm": per_arm,
                               "branch": verdict, "regression": fit,
                               "sesoi": SESOI, "n_boot": N_BOOT,
                               "boot_seed": BOOT_SEED}, indent=1))
    print(f"\nwrote {out.name}")


if __name__ == "__main__":
    main()
