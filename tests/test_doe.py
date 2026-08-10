"""The sequential-DoE arm of Experiment 2 — what a practitioner does instead of BO.

Person A owns this. It is the comparator that makes E2 a domain claim rather than a
methods claim: not "our BO beats random search" but "our BO beats the procedure the
published study actually ran".

Two things here carry more weight than they look:

**Stage 4 is not optional.** The pipeline's output is a *predicted* optimum, and if it
is never measured, the arm's best-so-far is just its best design point and the thing
the method actually produced never enters the regret curve. The published study
evaluated its predicted optimum; so must this.

**The confirmation run is E4a seen from the other side.** It is scored with B's shared
`over_prediction_at_constrained_argmax`, so the two experiments produce one number
rather than two that disagree. If it lands outside its own design region and
under-delivers, the published failure mode has reproduced in the benchmark without
being staged for it.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.doe import DoEResult, run_doe_arm
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

D = 6
BUDGET = 48


class CountingOracle:
    """Wraps the real oracle and counts every measurement it hands out."""

    def __init__(self, seed: int = 0):
        self._o = BiphasicOracle(load_ensemble(dim=D)[0], sigma_rel=0.10, seed=seed)
        self.n_evaluated = 0
        self.batches: list[int] = []

    @property
    def x_star(self):
        return self._o.x_star

    def truth(self, X):
        return self._o.truth(X)

    def evaluate(self, X):
        self.n_evaluated += X.shape[0]
        self.batches.append(X.shape[0])
        return self._o.evaluate(X)


@pytest.fixture
def bounds():
    return torch.stack([torch.zeros(D, dtype=torch.double),
                        torch.ones(D, dtype=torch.double)])


@pytest.fixture(scope="module")
def result():
    o = CountingOracle()
    res = run_doe_arm(
        o,
        torch.stack([torch.zeros(D, dtype=torch.double),
                     torch.ones(D, dtype=torch.double)]),
        truth=o.truth, budget=BUDGET, seed=0,
    )
    return o, res


# --------------------------------------------------------------------- the budget
def test_the_arm_spends_exactly_the_shared_budget(result):
    """Identical total budget for every method, or E2 compares nothing."""
    o, res = result
    assert o.n_evaluated == BUDGET


def test_the_budget_splits_47_design_runs_plus_one_confirmation(result):
    _, res = result
    assert res.n_stage1 == 20                       # 2^(6-2) resolution IV + 4 centre
    assert res.n_stage2 == 27                       # 16 + 8 axial + 3 centre, on 4 factors
    assert res.n_stage1 + res.n_stage2 == 47
    assert res.n_confirmation == 1


def test_a_budget_that_cannot_be_split_raises_rather_than_truncating(bounds):
    """Silently spending 47 or 49 would make the arm incomparable and nothing would
    notice. Fail loudly instead."""
    o = CountingOracle()
    with pytest.raises(ValueError, match="budget"):
        run_doe_arm(o, bounds, truth=o.truth, budget=40, seed=0)


# ---------------------------------------------------------------------- the curve
def test_the_curve_is_best_so_far_and_never_decreases(result):
    _, res = result
    assert res.curve.shape == (BUDGET,)
    assert np.all(np.diff(res.curve) >= -1e-12)


def test_stage_four_actually_enters_the_regret_curve(result):
    """The whole point. The final curve entry must reflect the confirmation run
    having been measured, not merely predicted."""
    _, res = result
    assert res.confirmation_y is not None
    assert res.curve[-1] == pytest.approx(
        max(res.curve[-2], res.confirmation_y), abs=1e-12
    )


# --------------------------------------------------------------------- the screen
def test_it_screens_down_to_four_factors(result):
    """Matching the published 6 -> 4 reduction, which the oracle's active/inert
    structure gives the screen something real to find."""
    _, res = result
    assert len(res.kept_factors) == 4
    assert set(res.kept_factors) <= set(range(D))


def test_dropped_factors_are_held_at_a_recorded_level(result):
    """'Record which level dropped factors are held at' — otherwise stage 2's design
    region is undefined and the confirmation point cannot be interpreted."""
    _, res = result
    dropped = set(range(D)) - set(res.kept_factors)
    assert set(res.dropped_held_at) == dropped
    for level in res.dropped_held_at.values():
        assert 0.0 <= level <= 1.0


def test_the_registered_default_holds_dropped_factors_at_the_best_stage_one_level(result):
    """Q15 T2, PRE-REGISTERED: ``best_stage1`` is the primary and therefore the default.

    Registered on conservatism, before either arm was run — see OPEN-QUESTIONS Q15.
    A default that silently became ``zero`` would swap the primary for the sensitivity
    without anything failing, which is exactly the class of silent substitution T8 was
    written to stop.
    """
    o, res = result
    assert res.hold_dropped_at == "best_stage1"
    # Not all-zero: the best stage-1 run is a factorial corner or a centre point, so
    # at least one dropped factor sits off zero. If every level were 0.0 the default
    # would be indistinguishable from the sensitivity arm.
    assert any(level != 0.0 for level in res.dropped_held_at.values())


def test_holding_dropped_factors_at_zero_actually_holds_them_at_zero(bounds):
    """Q15's declared sensitivity arm — closer to Hall/Ogle, whose reported optimum
    sits at zero for both dropped laminins."""
    o = CountingOracle()
    res = run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=0,
                      hold_dropped_at="zero")
    assert res.hold_dropped_at == "zero"
    dropped = set(range(D)) - set(res.kept_factors)
    assert set(res.dropped_held_at) == dropped
    assert all(level == 0.0 for level in res.dropped_held_at.values())
    assert o.n_evaluated == BUDGET  # the sensitivity arm is not cheaper


def test_an_unrecognised_hold_policy_raises_rather_than_defaulting(bounds):
    """A typo must not silently fall back to the primary — that would report the
    sensitivity arm's filename against the primary arm's numbers."""
    o = CountingOracle()
    with pytest.raises(ValueError, match="hold_dropped_at"):
        run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=0,
                    hold_dropped_at="centre")


def test_the_two_hold_policies_are_genuinely_different_runs(bounds):
    """If both policies produced identical confirmation points the sensitivity would
    be vacuous — the Q15 stage2_half_width=0.5 failure mode in a new place."""
    o1 = CountingOracle()
    a = run_doe_arm(o1, bounds, truth=o1.truth, budget=BUDGET, seed=0,
                    hold_dropped_at="best_stage1")
    o2 = CountingOracle()
    b = run_doe_arm(o2, bounds, truth=o2.truth, budget=BUDGET, seed=0,
                    hold_dropped_at="zero")
    assert not torch.allclose(a.confirmation_x, b.confirmation_x)


def test_the_screen_finds_the_oracles_genuinely_active_factors():
    """A sanity check on the arm, not on the oracle: with a 4.5x influence ratio the
    screen should mostly recover the planted active set. Not all four every time --
    at sigma_rel = 0.10 on 20 runs it is a real screen, not an oracle -- so this
    asserts a majority across instances rather than perfection on one."""
    hits = []
    for inst in load_ensemble(dim=D)[:6]:
        o = BiphasicOracle(inst, sigma_rel=0.10, seed=0)
        b = torch.stack([torch.zeros(D, dtype=torch.double),
                         torch.ones(D, dtype=torch.double)])
        res = run_doe_arm(o, b, truth=o.truth, budget=BUDGET, seed=0)
        hits.append(len(set(res.kept_factors) & set(inst.active_idx.tolist())))
    assert np.mean(hits) >= 2.5, f"screen recovered {np.mean(hits):.2f}/4 active factors"


# -------------------------------------------------- the shared over-prediction number
def test_over_prediction_is_predicted_minus_the_noiseless_truth(result):
    """Computed with B's shared metric so A's confirmation run and B's E4a are one
    number. Must be scored against the NOISELESS value -- a noisy draw would widen
    the distribution for a reason unrelated to extrapolation."""
    o, res = result
    truth_there = float(o.truth(res.confirmation_x.unsqueeze(0)))
    assert res.over_prediction == pytest.approx(res.predicted_y - truth_there, abs=1e-9)


def test_the_confirmation_run_is_not_scored_with_the_noisy_measurement(result):
    """`confirmation_y` is what the lab saw; over-prediction uses the truth. If these
    were the same object the metric would silently absorb observation noise."""
    _, res = result
    assert res.confirmation_y != pytest.approx(res.predicted_y - res.over_prediction,
                                               abs=1e-12)


# ------------------------------------------------------------------- reproducibility
def test_the_arm_is_deterministic_given_a_seed(bounds):
    o1, o2 = CountingOracle(), CountingOracle()
    a = run_doe_arm(o1, bounds, truth=o1.truth, budget=BUDGET, seed=7)
    b = run_doe_arm(o2, bounds, truth=o2.truth, budget=BUDGET, seed=7)
    np.testing.assert_allclose(a.curve, b.curve)
    assert a.kept_factors == b.kept_factors
    torch.testing.assert_close(a.confirmation_x, b.confirmation_x)


def test_stage_two_explores_a_sub_region_not_the_whole_space(result):
    """'CCD **centred on the best stage-1 region**' — stage 2 is a local exploration.

    If stage 2 spanned the full range of the kept factors, `confirmation_inside_stage2`
    could never be False and the escape statistic would be vacuously 0%. The first
    version of this module had exactly that defect: it reported 0% escape across 40
    runs, which looked like a clean negative result and was actually a tautology.
    """
    _, res = result
    lo, hi = res.stage2_bounds
    full = hi - lo
    assert torch.all(full < 1.0 - 1e-9), (
        "stage 2 spans the entire factor range, so the predicted optimum cannot "
        "possibly fall outside it and the escape statistic means nothing"
    )
    assert torch.all(full > 0)


def test_the_predicted_optimum_is_searched_beyond_the_stage_two_region(result):
    """A practitioner reads the profiler over the ingredient ranges they care about,
    not only the sub-box they last measured in. Confining the search to stage 2 would
    make escape impossible by construction — the same tautology from the other side."""
    _, res = result
    lo, hi = res.search_bounds
    s_lo, s_hi = res.stage2_bounds
    assert torch.all(lo <= s_lo + 1e-12) and torch.all(hi >= s_hi - 1e-12)
    assert torch.any(hi - lo > s_hi - s_lo)


def test_it_also_reports_a_truth_scored_curve(result):
    """OPEN-QUESTIONS Q17. Every E2 arm must be scored on the noiseless value of the
    points it selected, or an arm can win by drawing lucky noise — and the size of
    that advantage differs by arm, so it does not cancel.

    `curve` is what the lab saw; `curve_true` is what was really there. The second is
    what E2 uses, and unlike the first it can never exceed the true optimum.
    """
    _, res = result
    assert res.curve_true.shape == res.curve.shape
    assert np.all(np.diff(res.curve_true) >= -1e-12)
    assert res.X_visited.shape == (BUDGET, D)


def test_the_truth_scored_curve_cannot_beat_the_optimum(result):
    """The check that catches the bug E1 exposed: an observation-scored curve CAN
    exceed the optimum, which is how we found the problem in the first place."""
    o, res = result
    assert float(res.curve_true[-1]) <= float(o._o.instance.optimum_value) + 1e-9


def test_it_returns_the_documented_shape(result):
    _, res = result
    assert isinstance(res, DoEResult)
    assert res.stationary_kind in {"maximum", "minimum", "saddle", "ridge"}
