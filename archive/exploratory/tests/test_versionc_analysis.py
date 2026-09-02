"""Version C section 0's analysis: the branch, the arm table, and the n_eff regression."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_analyse_versionc_gate", ROOT / "scripts" / "analyse_versionc_gate.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


def _rows(n=50, arm="versionb", regret_p=0.085, n_eff=2, sigma=0.10):
    return [{"instance": f"i{i}", "seed": 0, "arm": arm, "sigma": sigma,
             "regret_a": regret_p + 0.04, "regret_p": regret_p,
             "n_eff": n_eff, "sigma_over_sqrt_n_eff": sigma / n_eff ** 0.5}
            for i in range(n)]


def test_holm_is_monotone_and_never_below_the_raw_p():
    raw = [0.001, 0.02, 0.04, 0.5]
    adj = A._holm(raw)
    assert all(a >= r for a, r in zip(adj, raw))
    assert adj == sorted(adj)


def test_holm_on_a_single_test_returns_it_unchanged():
    assert A._holm([0.031]) == [0.031]


def test_the_branch_reads_the_named_arm_not_the_best_arm():
    """Section 0's branch is about SPADE's own rule-P regret. Reading the best arm's
    number instead would make the gate fire on whichever arm happened to win, which is a
    different question and a much easier one."""
    rows = _rows(arm="versionb", regret_p=0.20) + _rows(arm="qlognei", regret_p=0.05)
    verdict = A.branch_for(rows, arm="versionb")
    assert verdict["arm"] == "versionb"
    assert verdict["branch"] == "SEARCH_DEFICIT"
    assert verdict["mean_regret_p"] == pytest.approx(0.20)


def test_the_branch_is_the_runners_own_registered_function():
    """One definition, imported, so the analysis cannot drift from the runner."""
    assert A.gate_branch(0.085) == "IDENTIFICATION_ARTEFACT"
    assert A.gate_branch(0.12) == "SEARCH_DEFICIT"
    assert A.gate_branch(0.10) == "INCONCLUSIVE"


def test_the_regression_recovers_a_planted_slope_of_one():
    """`regret_P ~ sigma / sqrt(n_eff)` is the model behind section 2.2's well-count
    formula. If the slope is not near 1 that formula has no basis and must be replaced by
    empirical calibration -- so the regression has to be able to find a slope of 1 when
    one is there."""
    rng = np.random.default_rng(0)
    rows = []
    for sigma in (0.10, 0.25):
        for n_eff in (1, 2, 4, 8, 16):
            x = sigma / n_eff ** 0.5
            for _ in range(20):
                rows.append({"arm": "a", "sigma": sigma, "n_eff": n_eff,
                             "sigma_over_sqrt_n_eff": x,
                             "regret_p": x + rng.normal(0, 0.002)})
    fit = A.n_eff_regression(rows)
    assert fit["slope"] == pytest.approx(1.0, abs=0.05)
    assert fit["r2"] > 0.9
    assert fit["n"] == 200


def test_the_regression_reports_a_low_r2_rather_than_hiding_it():
    """The falsifying case must come back as a NUMBER, not as an exception. If the
    sigma/sqrt(n_eff) model does not hold, section 2.2's well-count formula has no basis
    -- and that has to be visible in the results file rather than crash the analysis."""
    rng = np.random.default_rng(1)
    rows = [{"arm": "a", "sigma": 0.1, "n_eff": int(n), "sigma_over_sqrt_n_eff": 0.1 / n ** 0.5,
             "regret_p": float(rng.normal(0.1, 0.05))}
            for n in rng.integers(1, 20, 100)]
    fit = A.n_eff_regression(rows)
    assert np.isfinite(fit["slope"])
    assert fit["r2"] < 0.5


def test_a_constant_n_eff_reports_the_slope_as_unidentified():
    """The degenerate design. Measured: an exact `std == 0` test leaves std ~1e-18 on a
    hundred copies of 0.07 -- float64 summation -- and a poorly-conditioned polyfit then
    returned a confident slope of 0.688 on constant x. The guard is relative."""
    rng = np.random.default_rng(1)
    rows = [{"arm": "a", "sigma": 0.1, "n_eff": 2, "sigma_over_sqrt_n_eff": 0.07,
             "regret_p": float(rng.normal(0.1, 0.05))} for _ in range(100)]
    fit = A.n_eff_regression(rows)
    assert np.isnan(fit["slope"])
    assert fit["slope_near_one"] is False
    assert "unidentified" in fit["note"]


def test_the_regression_refuses_a_single_sigma_silently(caplog):
    """Section 0 says 'across all arms and BOTH sigma'. A one-sigma fit is a different
    claim, so the result has to carry which sigmas it actually saw."""
    fit = A.n_eff_regression(_rows(n=40))
    assert fit["sigmas"] == [0.10]
    assert fit["both_sigma"] is False
