"""KF-3b / KF-3c / KF-3d for `spade-kf3-followup-2026-08-24`.

Registered in ``docs/SPADE-KF3-FOLLOWUP-SPEC.md`` §7, §8.1. Reuses the frozen study's own
statistical machinery (`paired_contrast`, `holm`, `containment_cell`) rather than
re-implementing it -- one Wilcoxon/bootstrap/Holm implementation in this project, not two.

    .venv/bin/python scripts/analyse_kf3_followup.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_final_spade_benchmark import (  # noqa: E402
    SESOI, containment_cell, holm, live_rows, paired_contrast)

#: The registered map cell reused from the combined study report (spec §7.1 borrows this
#: choice rather than inventing a new one -- see docs/SPADE-KF3-FOLLOWUP-SPEC.md §7).
TAU_FRAC, GAMMA, ALPHA = 0.25, 0.95, 0.95
CALIBRATION_CAP = 0.005  # frozen spec §7.5's cap, reused per §7's "exact bars" note

CONDITIONS = {
    "C2": ("results/final-spade-c2.json", "results/kf3-followup-c2-{arm}.json"),
    "C3": ("results/final-spade-c3.json", "results/kf3-followup-c3-{arm}.json"),
}
ARMS = ("spade_cf_erroraware", "spade_cf_diverse_batch")


def _rows(path: Path, arm_filter: str | None = None) -> list:
    data = json.loads(Path(path).read_text())
    rows = data["rows"]
    if arm_filter:
        rows = [r for r in rows if r["arm"] == arm_filter]
    return rows


def _murphy_calibration(rows: list, arm: str) -> float | None:
    """Mean Murphy calibration for one arm, at the registered map cell, live rows only."""
    sel = [r for r in live_rows(rows) if r["arm"] == arm
           and abs(float(r.get("tau_frac_or_quantile", -1)) - TAU_FRAC) < 1e-12
           and abs(float(r.get("gamma", -1)) - GAMMA) < 1e-12
           and abs(float(r.get("alpha", -1)) - ALPHA) < 1e-12
           and r.get("murphy_calibration") is not None]
    if not sel:
        return None
    vals = [float(r["murphy_calibration"]) for r in sel]
    return sum(vals) / len(vals)


def _certificate_downgrades(random_rows: list, new_rows: list, arm: str) -> list[str]:
    """Cells where `arm`'s cross-fit containment cell is not PASS while
    `spade_random_plate2`'s corresponding cell was -- spec §7's non-inferiority bar."""
    downgrades = []
    for gamma in (0.50, 0.95, 0.99):
        random_cell = containment_cell(random_rows, alpha=ALPHA, tau_frac=TAU_FRAC, gamma=gamma)
        new_cell = containment_cell(new_rows, alpha=ALPHA, tau_frac=TAU_FRAC, gamma=gamma)
        random_pass = (random_cell["n_nonempty"] >= 10
                       and random_cell["proportion"] is not None
                       and random_cell["exact_p"] is not None
                       and random_cell["exact_p"] >= 0.05)
        new_pass = (new_cell["n_nonempty"] >= 10
                    and new_cell["proportion"] is not None
                    and new_cell["exact_p"] is not None
                    and new_cell["exact_p"] >= 0.05)
        if random_pass and not new_pass:
            downgrades.append(f"gamma={gamma}: random PASS, {arm} not PASS "
                              f"(n_nonempty={new_cell['n_nonempty']}, "
                              f"exact_p={new_cell['exact_p']})")
    return downgrades


def main() -> None:
    results: dict = {}
    pvals: dict = {}

    for cond, (random_path, kf3_path_tmpl) in CONDITIONS.items():
        random_rows = _rows(ROOT / random_path, arm_filter="spade_random_plate2")
        random_cal = _murphy_calibration(random_rows, "spade_random_plate2")

        for arm in ARMS:
            arm_rows = _rows(ROOT / kf3_path_tmpl.format(arm=arm))
            combined = random_rows + arm_rows

            contrast = paired_contrast(combined, arm, "spade_random_plate2",
                                       "symmetric_difference_pred",
                                       tau_frac=TAU_FRAC, gamma=GAMMA, alpha=ALPHA)
            # `n25` (seeds averaged within instance) collapses to n=1 for a family
            # condition -- hartmann6 (C3) is one fixed landscape, not 25 Hill-ensemble
            # instances, so instance-averaging throws away all 100 campaigns' worth of
            # information and gives a trivial p=1.0/degenerate CI. Detected, not assumed:
            # fall back to n50 (the raw per-campaign paired unit) whenever n25 degenerates,
            # and say so in the record rather than silently reporting the useless number.
            unit = contrast["n25"] if contrast["n25"]["n"] > 1 else contrast["n50"]
            unit_used = "n25" if contrast["n25"]["n"] > 1 else "n50 (n25 degenerate, n=1)"
            effect = unit["mean"]  # mean(arm - random); negative = arm better
            beats_by_sesoi = (effect is not None and effect <= -SESOI)

            arm_cal = _murphy_calibration(arm_rows, arm)
            cal_ok = (random_cal is None or arm_cal is None
                     or (arm_cal - random_cal) <= CALIBRATION_CAP)

            cert_downgrades = _certificate_downgrades(random_rows, arm_rows, arm)

            key = f"{cond}:{arm}"
            pvals[key] = unit["wilcoxon_p"]
            results[key] = {
                "condition": cond, "arm": arm,
                "unit_used": unit_used,
                "symmetric_difference_effect": effect,
                "symmetric_difference_ci": [unit["ci_lo"], unit["ci_hi"]],
                "beats_random_by_sesoi": beats_by_sesoi,
                "wilcoxon_p": unit["wilcoxon_p"],
                "calibration_random": random_cal, "calibration_arm": arm_cal,
                "calibration_ok": cal_ok,
                "certificate_downgrades": cert_downgrades,
                "units_disagree": contrast["units_disagree"],
            }

    # --- F-KF3FU: Holm across all 4 tests together (spec §8.1) ---------------------------
    adjusted = holm(pvals)
    for key, p_holm in adjusted.items():
        results[key]["p_holm"] = p_holm

    # --- KF-3b / KF-3c verdicts: per spec §7.1/§7.2, PASS in >=1 condition suffices -----
    for arm in ARMS:
        cells = [results[f"{cond}:{arm}"] for cond in CONDITIONS]
        passes = [c for c in cells
                 if c["beats_random_by_sesoi"] and c["p_holm"] is not None and c["p_holm"] < 0.05
                 and c["calibration_ok"] and not c["certificate_downgrades"]]
        verdict = "PASS" if passes else "FAIL"
        print(f"\n{'='*80}\n{'KF-3b' if arm == 'spade_cf_erroraware' else 'KF-3c'}"
              f" -- {arm}: {verdict}\n{'='*80}")
        for cond in CONDITIONS:
            c = results[f"{cond}:{arm}"]
            print(f"  {cond} [{c['unit_used']}]: effect={c['symmetric_difference_effect']:+.5f} "
                  f"CI={c['symmetric_difference_ci']} p_holm={c['p_holm']:.4g} "
                  f"beats_sesoi={c['beats_random_by_sesoi']} "
                  f"cal_ok={c['calibration_ok']} "
                  f"cert_downgrades={c['certificate_downgrades'] or 'none'}")

    both_pass = all(
        any(results[f"{cond}:{arm}"]["beats_random_by_sesoi"]
            and results[f"{cond}:{arm}"]["p_holm"] is not None
            and results[f"{cond}:{arm}"]["p_holm"] < 0.05
            and results[f"{cond}:{arm}"]["calibration_ok"]
            and not results[f"{cond}:{arm}"]["certificate_downgrades"]
            for cond in CONDITIONS)
        for arm in ARMS)
    print(f"\n{'='*80}\nKF-3d gating: "
          f"{'BOTH KF-3b and KF-3c PASS -- combined arm may be built' if both_pass else 'MOOT -- at least one of KF-3b/KF-3c did not PASS, combined arm is not built'}"
          f"\n{'='*80}")

    out = ROOT / "results" / "kf3-followup-analysis.json"
    out.write_text(json.dumps({
        "study_id": "spade-kf3-followup-2026-08-24",
        "map_cell": {"tau_frac": TAU_FRAC, "gamma": GAMMA, "alpha": ALPHA},
        "results": results,
        "kf3d_gate": "build" if both_pass else "moot",
    }, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
