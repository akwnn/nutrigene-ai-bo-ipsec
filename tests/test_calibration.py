"""Murphy's calibration-refinement decomposition of the Brier score.

Registered in `docs/OPEN-QUESTIONS.md` under P7 / Amendment A5, committed at 5c44e6a
before this file existed. The registered specification, restated so the tests can be
read against it without opening the other document:

    Brier = calibration - refinement + uncertainty          (Murphy 1973)

    10 EQUAL-COUNT bins over the predicted probability. Not equal-width: prevalence at
    tau_frac=0.95 is 0.003, so equal-width bins are empty exactly where these maps live.

    The identity is the arbiter. It must hold to 1e-10 on every row, or the
    decomposition is wrong and the row is not written.

WHY THE DECOMPOSED QUANTITY IS THE BINNED BRIER, AND WHY THAT IS NOT A DODGE
----------------------------------------------------------------------------
Murphy (1973) is stated for a forecast taking finitely many values, where the bins ARE
the distinct forecast values. Applied to a continuous forecast through binning, the
three-term identity is exact for the *binned* forecast and inexact for the raw one --
the gap is the within-bin term `mean_k n_k [var_k(p) - 2 cov_k(p, o)]`, which no choice
of sign convention removes. So `brier` here is the Brier score of the binned forecast,
which the identity governs exactly, and `brier_raw` is the project's published quantity
(`designspace.brier_and_auc`), carried alongside with the gap named as `within_bin`.
Hiding the gap inside a redefined "calibration" would make the identity hold by
construction and test nothing.
"""

import numpy as np
import pytest
import torch

from boec.calibration import equal_count_bins, murphy_decomposition
from boec.designspace import brier_and_auc

N_BINS = 10


def _identity_residual(d: dict) -> float:
    return abs(d["calibration"] - d["refinement"] + d["uncertainty"] - d["brier"])


def _truth_for(label: torch.Tensor) -> torch.Tensor:
    """A `truth` vector whose `>= 0.5` indicator is exactly `label`."""
    return torch.where(label.bool(), 1.0, 0.0).double()


# --- the identity, which is the arbiter -------------------------------------------

def test_identity_holds_to_1e_10_on_a_random_map():
    """calibration - refinement + uncertainty == brier. The registered check."""
    g = torch.Generator().manual_seed(0)
    p = torch.rand(5000, generator=g, dtype=torch.double)
    label = (torch.rand(5000, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert _identity_residual(d) <= 1e-10


def test_identity_holds_at_the_tail_prevalence_these_maps_actually_live_at():
    """Prevalence 0.003 on a 20,000-point grid -- the tau_frac=0.95 cell."""
    g = torch.Generator().manual_seed(1)
    p = torch.rand(20_000, generator=g, dtype=torch.double) ** 6
    label = (torch.rand(20_000, generator=g, dtype=torch.double) < 0.003).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert 0.001 < float(label.mean()) < 0.010
    assert _identity_residual(d) <= 1e-10


def test_identity_holds_for_a_saturated_map():
    """cdf() of a large z is exactly 1.0 in float64, so real maps carry heavy ties."""
    p = torch.cat([torch.ones(9_000, dtype=torch.double),
                   torch.zeros(9_000, dtype=torch.double),
                   torch.rand(2_000, generator=torch.Generator().manual_seed(2),
                              dtype=torch.double)])
    label = (torch.rand(20_000, generator=torch.Generator().manual_seed(3),
                        dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert _identity_residual(d) <= 1e-10


# --- equal-count, which is the registered choice ----------------------------------

def test_bins_are_equal_count_when_the_forecast_has_no_ties():
    g = torch.Generator().manual_seed(4)
    p = torch.rand(1000, generator=g, dtype=torch.double)
    idx = equal_count_bins(p, N_BINS)
    counts = torch.bincount(idx, minlength=N_BINS)
    assert counts.tolist() == [100] * N_BINS


def test_equal_count_populates_the_tail_where_equal_width_would_not():
    """The registered reason for equal-count, on the shape these maps actually have.

    A probability map at tau_frac=0.95 is a mass of near-zero probabilities with a thin
    high tail and almost nothing between: prevalence is 0.00294. Equal-width bins are
    then empty across the whole middle, and an empty bin contributes to neither term.
    """
    g = torch.Generator().manual_seed(5)
    p = torch.cat([0.02 + 0.06 * torch.rand(990, generator=g, dtype=torch.double),
                   torch.full((10,), 0.97, dtype=torch.double)])
    d = murphy_decomposition(p, _truth_for((p > 0.5).double()), tau=0.5, n_bins=N_BINS)
    assert d["bin_counts"] == [100] * N_BINS
    width_counts, _ = np.histogram(p.numpy(), bins=N_BINS, range=(0.0, 1.0))
    assert (width_counts == 0).sum() >= 8, "equal-width should starve the middle here"


def test_ties_are_never_split_across_bins():
    """A calibration function must be a function OF the forecast value.

    Splitting identical forecasts into two bins with different observed frequencies
    would manufacture refinement out of nothing but rank order.
    """
    p = torch.tensor([0.2] * 400 + [0.6] * 300 + [0.9] * 300, dtype=torch.double)
    idx = equal_count_bins(p, N_BINS)
    for v in (0.2, 0.6, 0.9):
        assert len(set(idx[p == v].tolist())) == 1


# --- the terms mean what they are named -------------------------------------------

def test_calibration_is_zero_for_a_perfectly_calibrated_forecast():
    """Ten distinct forecast values, each realised at exactly its own frequency."""
    ps, labels = [], []
    for k in range(N_BINS):
        pk = (k + 0.5) / N_BINS
        n_pos = int(round(200 * pk))
        ps.append(torch.full((200,), pk, dtype=torch.double))
        labels.append(torch.cat([torch.ones(n_pos, dtype=torch.double),
                                 torch.zeros(200 - n_pos, dtype=torch.double)]))
    p, label = torch.cat(ps), torch.cat(labels)
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["calibration"] < 1e-12
    assert _identity_residual(d) <= 1e-10


def test_refinement_is_zero_for_a_constant_forecast():
    """One bin, so every observed frequency equals the base rate. No resolution."""
    p = torch.full((1000,), 0.3, dtype=torch.double)
    g = torch.Generator().manual_seed(6)
    label = (torch.rand(1000, generator=g, dtype=torch.double) < 0.4).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["refinement"] < 1e-12
    assert d["bin_counts"] == [1000]
    assert _identity_residual(d) <= 1e-10


def test_refinement_equals_uncertainty_for_a_perfect_forecast():
    """p == the outcome: brier 0, calibration 0, refinement carries all of it."""
    g = torch.Generator().manual_seed(7)
    label = (torch.rand(1000, generator=g, dtype=torch.double) < 0.35).double()
    d = murphy_decomposition(label, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["brier"] < 1e-12
    assert d["calibration"] < 1e-12
    assert abs(d["refinement"] - d["uncertainty"]) < 1e-12


def test_uncertainty_is_the_base_rate_variance():
    g = torch.Generator().manual_seed(8)
    label = (torch.rand(2000, generator=g, dtype=torch.double) < 0.2).double()
    p = torch.rand(2000, generator=g, dtype=torch.double)
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    o = float(label.mean())
    assert abs(d["uncertainty"] - o * (1 - o)) < 1e-12


# --- the degenerate cases, each returning deliberately ----------------------------

def test_empty_input_returns_none_not_a_number():
    """The `vorobev.empirical_containment` convention: nothing measured, nothing said."""
    empty = torch.zeros(0, dtype=torch.double)
    assert murphy_decomposition(empty, empty, tau=0.5, n_bins=N_BINS) is None


def test_all_one_class_gives_zero_uncertainty_and_zero_refinement_and_says_so():
    """Refinement is 0 BY CONSTRUCTION here, so the cell can rank nothing.

    It is returned as the exact 0.0 it is -- nan would break the registered identity
    check, which must hold on every row -- and flagged so no ranking can consume it.
    """
    g = torch.Generator().manual_seed(9)
    p = torch.rand(1000, generator=g, dtype=torch.double)
    for label in (torch.zeros(1000, dtype=torch.double),
                  torch.ones(1000, dtype=torch.double)):
        d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
        assert d["uncertainty"] == 0.0
        assert d["refinement"] == 0.0
        assert "single_class" in d["degenerate"]
        assert _identity_residual(d) <= 1e-10


def test_fewer_distinct_probabilities_than_bins_collapses_and_says_so():
    p = torch.tensor([0.1] * 400 + [0.5] * 400 + [0.8] * 200, dtype=torch.double)
    g = torch.Generator().manual_seed(10)
    label = (torch.rand(1000, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert len(d["bin_counts"]) == 3
    assert sum(d["bin_counts"]) == 1000
    assert "few_bins" in d["degenerate"]
    assert _identity_residual(d) <= 1e-10


def test_a_single_member_bin_is_flagged_and_the_identity_still_holds():
    """One point alone in a bin makes its observed frequency exactly 0 or 1."""
    p = torch.cat([torch.zeros(999, dtype=torch.double),
                   torch.ones(1, dtype=torch.double)])
    label = torch.cat([torch.zeros(999, dtype=torch.double),
                       torch.ones(1, dtype=torch.double)])
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert 1 in d["bin_counts"]
    assert "singleton_bin" in d["degenerate"]
    assert _identity_residual(d) <= 1e-10


def test_a_clean_map_carries_no_degenerate_flag():
    g = torch.Generator().manual_seed(11)
    p = torch.rand(5000, generator=g, dtype=torch.double)
    label = (torch.rand(5000, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["degenerate"] == []


# --- the tie back to the number the project has already published -----------------

def test_brier_raw_is_bitwise_the_published_brier():
    """`brier_raw` must BE `designspace.brier_and_auc`'s Brier, not a re-derivation.

    Everything P7 says about "the sum" is a statement about that committed column, so a
    decomposition that quietly scored a different quantity would answer another question.
    """
    g = torch.Generator().manual_seed(12)
    p = torch.rand(4000, generator=g, dtype=torch.double)
    truth = torch.rand(4000, generator=g, dtype=torch.double)
    tau = 0.7
    d = murphy_decomposition(p, truth, tau=tau, n_bins=N_BINS)
    published, _ = brier_and_auc(p, truth, tau)
    assert d["brier_raw"] == published


def test_binning_a_calibrated_informative_forecast_makes_it_score_worse():
    """`within_bin = brier_raw - brier` is NEGATIVE here, and that is the right sign.

    The gap is `mean_k n_k [var_k(p) - 2 cov_k(p, o)]`. A calibrated forecast has
    `cov_k(p, o) ~ var_k(p)` inside a bin, so the gap goes to `-var_k(p)`: replacing the
    forecast by its bin mean throws away resolution the raw forecast really had, and the
    binned score is the worse one. An earlier version of this test asserted the opposite
    sign from the phrase "binning costs something"; the test was wrong, not the code.
    """
    g = torch.Generator().manual_seed(13)
    p = torch.rand(4000, generator=g, dtype=torch.double)
    label = (torch.rand(4000, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert abs(d["within_bin"] - (d["brier_raw"] - d["brier"])) <= 1e-12
    assert d["within_bin"] < 0
    assert d["brier"] > d["brier_raw"]


def test_binning_away_pointless_scatter_makes_the_score_better():
    """The other sign, pinned so neither is mistaken for a bug.

    Forecast noise uncorrelated with the outcome inside a bin gives `cov_k = 0`, so the
    gap is `+var_k(p)`: the bin mean is the better forecast and `within_bin` is positive.
    """
    g = torch.Generator().manual_seed(16)
    label = (torch.rand(4000, generator=g, dtype=torch.double) < 0.4).double()
    p = (0.4 + 0.15 * torch.randn(4000, generator=g, dtype=torch.double)).clamp(0.01, 0.99)
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["within_bin"] > 0
    assert d["brier"] < d["brier_raw"]


def test_within_bin_vanishes_when_the_forecast_is_already_discrete():
    """No within-bin scatter, so the raw and binned Brier coincide and the classical
    three-term identity holds against the raw score itself."""
    p = torch.tensor([0.15] * 500 + [0.45] * 500 + [0.85] * 500, dtype=torch.double)
    g = torch.Generator().manual_seed(14)
    label = (torch.rand(1500, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert abs(d["within_bin"]) < 1e-15
    assert abs(d["calibration"] - d["refinement"] + d["uncertainty"]
               - d["brier_raw"]) <= 1e-10


def test_bin_counts_are_reported_in_ascending_forecast_order():
    p = torch.tensor([0.9] * 100 + [0.1] * 300 + [0.5] * 600, dtype=torch.double)
    g = torch.Generator().manual_seed(15)
    label = (torch.rand(1000, generator=g, dtype=torch.double) < p).double()
    d = murphy_decomposition(p, _truth_for(label), tau=0.5, n_bins=N_BINS)
    assert d["bin_counts"] == [300, 600, 100]


# --- the registered decision rule, tested on synthetic rows ------------------------
#
# P7's deliverable is a VERDICT, and a bug in the ranking comparison would produce a
# wrong one silently -- the numbers would all be right and the conclusion wrong. The
# rule is therefore exercised directly, on rows built so the answer is known by
# construction rather than measured.

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_p7_murphy.py"


def _p7():
    spec = importlib.util.spec_from_file_location("p7_murphy", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rows(refinement_by_arm: dict, n: int = 12, gamma: float = 0.50,
          tau_frac: float = 0.60, flag_on: tuple | None = None) -> list[dict]:
    """Rows whose Brier ordering is fixed and whose refinement ordering is chosen.

    `brier_raw` is set so the arms rank a-b-c-... by Brier; `refinement` is whatever the
    caller passes. Uncertainty is constant across arms, as it is in the real data --
    it is a function of the truth and tau alone.
    """
    out = []
    for i in range(n):
        for a, ref in refinement_by_arm.items():
            cal = 0.4 + 0.01 * sorted(refinement_by_arm).index(a)
            out.append({
                "instance": f"i{i}", "seed": 0, "arm": a, "gamma": gamma,
                "tau_frac": tau_frac, "true_frac_above_tau": 0.3, "regret": 0.1,
                **{f"{mp}_{k}": v for mp in ("pred", "latent") for k, v in {
                    "brier_raw": cal + 0.001 * i, "brier": cal + 0.001 * i,
                    "refinement": ref + 0.0001 * i, "calibration": cal,
                    "uncertainty": 0.21, "within_bin": 0.0,
                    "degenerate": (["single_class"]
                                   if flag_on == (f"i{i}", a) else []),
                }.items()},
            })
    return out


def test_the_rule_returns_a_null_when_refinement_orders_the_arms_as_brier_does():
    """Refinement decreasing exactly as Brier increases: the orderings coincide."""
    p7 = _p7()
    s = p7.summarise(_rows({"a": 0.30, "b": 0.20, "c": 0.10}))
    cell = s["cells"][0]
    assert cell["pred"]["rank_by_brier"] == ["a", "b", "c"]
    assert cell["pred"]["rank_by_refinement"] == ["a", "b", "c"]
    assert cell["pred"]["rankings_agree"]
    assert cell["pred"]["agreement"]["n_pair_inversions"] == 0
    assert cell["pred"]["agreement"]["spearman_rho"] == 1.0
    assert s["verdict"].startswith("A5 IS A NULL")


def test_the_rule_fires_when_a_single_pair_is_inverted():
    p7 = _p7()
    s = p7.summarise(_rows({"a": 0.20, "b": 0.30, "c": 0.10}))
    cell = s["cells"][0]
    assert cell["pred"]["rank_by_brier"] == ["a", "b", "c"]
    assert cell["pred"]["rank_by_refinement"] == ["b", "a", "c"]
    assert not cell["pred"]["rankings_agree"]
    assert cell["pred"]["inversions"] == [["a", "b"]]
    assert s["verdict"].startswith("A5 FOUND SOMETHING")
    assert [t["pair"] for t in s["inversion_tests"] if t["map"] == "pred"] == [["a", "b"]]
    assert "holm_p" in s["inversion_tests"][0]["refinement"]


def test_uncertainty_carries_no_across_arm_spread():
    """The pipeline self-check: a nonzero spread means the arms saw different truths."""
    p7 = _p7()
    s = p7.summarise(_rows({"a": 0.30, "b": 0.20, "c": 0.10}))
    assert s["worst_uncertainty_across_arm_spread"] == 0.0


def test_a_single_class_campaign_is_dropped_for_EVERY_arm_not_just_the_flagged_one():
    """Refinement is 0 by construction there, so the cell can rank nothing.

    Dropping must be arm-symmetric or the drop itself becomes a contrast: the truth does
    not depend on the arm, so a campaign degenerate for one arm is degenerate for all.
    """
    p7 = _p7()
    s = p7.summarise(_rows({"a": 0.30, "b": 0.20, "c": 0.10}, flag_on=("i3", "a")))
    cell = s["cells"][0]
    assert cell["n_single_class_dropped"] == 1
    assert cell["n_used"] == 11
    for t in s["inversion_tests"]:
        assert t["refinement"]["n"] == 11


def test_holm_agrees_with_the_implementation_already_in_the_repo():
    p7 = _p7()
    spec = importlib.util.spec_from_file_location(
        "q39", Path(__file__).resolve().parents[1] / "scripts/run_q39_multiplicity.py")
    q39 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q39)
    ps = [0.001, 0.04, 0.2, 0.5, 0.011, 0.9]
    assert p7._holm(ps) == pytest.approx(q39.holm(ps))
