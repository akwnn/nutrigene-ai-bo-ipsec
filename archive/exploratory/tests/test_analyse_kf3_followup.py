"""Regression test for the n25-degenerate-unit bug caught while running
`scripts/analyse_kf3_followup.py` against real C3 (hartmann6) data.

`paired_contrast`'s `n25` unit (seeds averaged within instance) collapses to `n=1` for any
condition with exactly one real "instance" -- every non-Hill family condition, since
`run_final_spade_benchmark._keys` keys family campaigns as `(family, seed)` with the SAME
`family` string standing in for `instance` on every row. A degenerate n25 gives a trivial
Wilcoxon p=1.0 and a zero-width CI regardless of the true effect, which would have silently
forced every family-condition KF-3b/KF-3c cell to look non-significant. Caught by hand
before trusting the first real run's C3 numbers; this test locks the detection in.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_final_spade_benchmark import paired_contrast  # noqa: E402


def _row(arm, instance, seed, value):
    return {
        "arm": arm, "family": "hartmann6", "dimension": 6, "sigma": 0.25,
        "instance_seed": instance, "campaign_seed": seed,
        "tau_frac_or_quantile": 0.25, "gamma": 0.95, "alpha": 0.95,
        "symmetric_difference_pred": value,
        "unavailable_reason": None,
    }


def test_n25_collapses_to_one_and_n50_stays_the_real_sample_size_for_a_family_condition():
    """Every row shares the SAME instance ("hartmann6") the way a real family condition
    does -- n25 must degenerate to n=1 while n50 keeps the real per-campaign count."""
    rows = []
    for seed in range(10):
        rows.append(_row("spade_cf_erroraware", "hartmann6", seed, 0.10 - 0.001 * seed))
        rows.append(_row("spade_random_plate2", "hartmann6", seed, 0.12))

    c = paired_contrast(rows, "spade_cf_erroraware", "spade_random_plate2",
                        "symmetric_difference_pred", tau_frac=0.25, gamma=0.95, alpha=0.95)

    assert c["n25"]["n"] == 1, "n25 should collapse to one instance for a family condition"
    assert c["n25"]["wilcoxon_p"] == 1.0, "a single-point Wilcoxon is trivially non-significant"
    assert c["n50"]["n"] == 10, "n50 must keep the real per-campaign sample size"
    assert c["n50"]["wilcoxon_p"] < 1.0


def test_unit_selection_rule_falls_back_to_n50_only_when_n25_is_degenerate():
    """The exact rule `analyse_kf3_followup.py` uses: n25 if it has more than one point,
    otherwise n50. A multi-instance condition (Hill-like) must keep using n25."""
    family_rows = []
    for seed in range(6):
        family_rows.append(_row("spade_cf_erroraware", "hartmann6", seed, 0.05))
        family_rows.append(_row("spade_random_plate2", "hartmann6", seed, 0.08))
    c_family = paired_contrast(family_rows, "spade_cf_erroraware", "spade_random_plate2",
                               "symmetric_difference_pred", tau_frac=0.25, gamma=0.95, alpha=0.95)
    assert (c_family["n25"] if c_family["n25"]["n"] > 1 else c_family["n50"]) is c_family["n50"]

    hill_rows = []
    for inst in ("i1", "i2", "i3"):
        for seed in range(2):
            r = _row("spade_cf_erroraware", inst, seed, 0.05)
            r["family"] = "hill"
            hill_rows.append(r)
            r2 = _row("spade_random_plate2", inst, seed, 0.08)
            r2["family"] = "hill"
            hill_rows.append(r2)
    c_hill = paired_contrast(hill_rows, "spade_cf_erroraware", "spade_random_plate2",
                             "symmetric_difference_pred", tau_frac=0.25, gamma=0.95, alpha=0.95)
    assert c_hill["n25"]["n"] == 3, "three distinct Hill instances should give n25=3"
    assert (c_hill["n25"] if c_hill["n25"]["n"] > 1 else c_hill["n50"]) is c_hill["n25"]
