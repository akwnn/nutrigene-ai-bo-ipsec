"""Two one-sided tests on n=25 paired landscape differences. SESOI = 0.02."""

from __future__ import annotations

import numpy as np
import pytest


def test_tost_calls_a_mean_inside_sesoi_equivalent():
    from boec.tost import tost_paired

    rng = np.random.default_rng(0)
    diffs = rng.normal(0.0, 0.004, 25)
    out = tost_paired(diffs, sesoi=0.02)
    assert out["equivalent"] is True
    assert out["verdict"] == "equivalent"
    assert out["sesoi"] == 0.02
    assert out["p_lower"] < 0.05 and out["p_upper"] < 0.05


def test_tost_calls_a_large_gap_different():
    from boec.tost import tost_paired

    rng = np.random.default_rng(0)
    diffs = rng.normal(-0.06, 0.01, 25)
    out = tost_paired(diffs, sesoi=0.02)
    assert out["equivalent"] is False
    assert out["verdict"] == "different"
    assert out["hi"] < 0 or out["lo"] > 0


def test_tost_calls_a_noisy_near_zero_inconclusive():
    from boec.tost import tost_paired

    rng = np.random.default_rng(1)
    diffs = rng.normal(0.0, 0.08, 25)
    out = tost_paired(diffs, sesoi=0.02)
    assert out["equivalent"] is False
    assert out["verdict"] == "inconclusive"
    assert out["lo"] <= 0 <= out["hi"]


def test_tost_rejects_a_nonpositive_sesoi():
    from boec.tost import tost_paired

    with pytest.raises(ValueError, match="sesoi"):
        tost_paired([0.0, 0.01], sesoi=0.0)


def test_tost_never_says_null_or_tie():
    from boec.tost import tost_paired

    rng = np.random.default_rng(2)
    out = tost_paired(rng.normal(0, 0.05, 25), sesoi=0.02)
    assert out["verdict"] in {"equivalent", "different", "inconclusive"}
    assert "null" not in out["verdict"]
    assert "tie" not in out["verdict"]


def test_wilcoxon_mde_is_positive_and_finite_at_n_25():
    from boec.tost import wilcoxon_mde

    mde = wilcoxon_mde(0.04, n=25, power=0.80, n_sim=400, seed=0)
    assert 0.01 < mde < 0.08


def test_wilcoxon_mde_grows_with_noise():
    from boec.tost import wilcoxon_mde

    quiet = wilcoxon_mde(0.02, n=25, power=0.80, n_sim=400, seed=0)
    noisy = wilcoxon_mde(0.06, n=25, power=0.80, n_sim=400, seed=0)
    assert noisy > quiet


def test_per_instance_mean_averages_two_seeds():
    from boec.tost import per_instance

    rows = [
        {"instance": "b", "seed": 0, "x": 0.10},
        {"instance": "b", "seed": 1, "x": 0.20},
        {"instance": "a", "seed": 0, "x": 0.00},
        {"instance": "a", "seed": 1, "x": 0.10},
    ]
    got = per_instance(rows, "x")
    assert list(got) == pytest.approx([0.05, 0.15])
