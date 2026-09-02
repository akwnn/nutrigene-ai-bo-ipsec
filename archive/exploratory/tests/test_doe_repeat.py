"""The registered doe_repeat budget policy — Q52 §2.

OPEN-QUESTIONS Q52 §2 DESIGN, committed before this file existed:

    Run the unmodified 48-evaluation pipeline with a fresh seed, repeatedly, carrying
    the best result forward; stop when the next full pipeline would exceed the cap. At
    a cap of 200 that is four complete pipelines = 192 evaluations, and the remaining 8
    are deliberately not spent -- a partial pipeline is not the method.

    Rule A: best observed over every point measured across all completed pipelines.
    Rule C: the recommendation of the pipeline whose stage-4 confirmation measured best.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.diagnostics import reported_best_curve
from boec.doe import run_doe_arm
from boec.doe_repeat import run_doe_repeat
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

BUDGET = 48


def _cell(seed: int = 0, sigma: float = 0.25):
    inst = load_ensemble(dim=6)[0]
    oracle = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    bounds = torch.stack([torch.zeros(6, dtype=torch.double),
                          torch.ones(6, dtype=torch.double)])
    return inst, oracle, bounds


def test_a_cap_of_200_buys_four_pipelines_and_leaves_eight_evaluations_unspent():
    """192, not 200. A partial pipeline is not the method."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    assert r.n_pipelines == 4
    assert r.evaluations_spent == 192


def test_the_checkpoints_are_the_multiples_of_the_pipeline_budget():
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    assert r.checkpoints == (48, 96, 144, 192)
    assert sorted(r.rule_a) == [48, 96, 144, 192]


def test_a_cap_below_one_pipeline_buys_nothing_rather_than_a_partial_design():
    """The classical arm cannot answer at 24 evaluations. That is censoring, and it
    must present as an empty curve rather than a truncated pipeline."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=47, seed=0)
    assert r.n_pipelines == 0
    assert r.evaluations_spent == 0
    assert r.rule_a == {}


def test_rule_a_is_scored_over_the_accumulated_measurement_set():
    """The contract of 'carrying the best forward': at each checkpoint the arm is
    scored over every point measured so far, not over the last pipeline alone."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    opt = float(inst.optimum_value)

    # A FRESH oracle: BiphasicOracle advances its noise stream on every evaluate, so
    # replaying the pipelines against the consumed instance would draw different
    # observations and compare two different experiments.
    _, fresh, _ = _cell()

    x_acc, y_acc = [], []
    for i, s in enumerate(r.seeds):
        one = run_doe_arm(fresh, bounds, truth=fresh.truth, budget=48, seed=s)
        x_acc.append(one.X_visited)
        y_acc.append(one.Y_visited)
        expected = opt - float(reported_best_curve(
            oracle.truth(torch.cat(x_acc)).double(), torch.cat(y_acc))[-1])
        assert r.rule_a[(i + 1) * 48] == pytest.approx(expected, abs=1e-12)


def test_rule_a_may_worsen_as_the_budget_grows_and_that_is_the_mechanism():
    """**Not a bug, and this test exists because the first version of it asserted the
    opposite.** Rule A picks by the running *observed* argmax, so every extra
    measurement is another chance for a noisy high reading at a mediocre point to
    become the incumbent. Q52 §1.1 measured exactly this on space-filling designs —
    rule A identification error rises 0.0432 -> 0.0746 from n=24 to n=384 at
    sigma_rel=0.10 — and P3 registers it as a prediction about the static arms. The
    classical arm inherits it because its design also spreads.

    Asserting monotone improvement here would have encoded the oracle-best intuition
    that voided E2's first run.
    """
    inst, oracle, bounds = _cell(sigma=0.25)
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    values = [r.rule_a[c] for c in r.checkpoints]
    assert max(values) > min(values), (
        "this instance happens not to exhibit the effect; the property under test is "
        f"that rule A is NOT constrained to improve, values={values}")


def test_each_pipeline_gets_a_distinct_seed():
    """Repeating the pipeline at one seed would measure the same 48 points four times
    and buy nothing at all."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=7)
    assert len(set(r.seeds)) == r.n_pipelines == 4


def test_rule_c_reports_the_pipeline_whose_confirmation_measured_best():
    """'Keep the best' under rule C is decided by the stage-4 confirmation, because
    that is the only signal a lab actually has when choosing between completed runs."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    best_at_end = int(np.argmax(r.confirmation_y[: r.n_pipelines]))
    assert r.chosen_pipeline[192] == best_at_end


def test_both_rule_c_scorings_are_reported_because_q41_requires_all_three():
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    assert sorted(r.rule_c_unconstrained) == [48, 96, 144, 192]
    assert sorted(r.rule_c_constrained) == [48, 96, 144, 192]


def test_the_constrained_recommendation_is_never_worse_than_the_unconstrained_one():
    """Q35 measured this at 200/200 runs: constraining the argmax to the region stage 2
    explored removes about three quarters of the recommendation error. It is a property
    of a saddle, so it must hold here too."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0)
    for c in r.checkpoints:
        assert r.rule_c_constrained[c] <= r.rule_c_unconstrained[c] + 1e-9


def test_the_run_is_reproducible_from_its_seed():
    inst, oracle_a, bounds = _cell()
    _, oracle_b, _ = _cell()
    a = run_doe_repeat(oracle_a, bounds, truth=oracle_a.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=3)
    b = run_doe_repeat(oracle_b, bounds, truth=oracle_b.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=3)
    assert a.rule_a == b.rule_a
    assert a.rule_c_unconstrained == b.rule_c_unconstrained


def test_a_cap_that_is_not_a_multiple_of_the_budget_floors_rather_than_raising():
    """Unlike run_doe_arm, which raises on an inexact budget, the repeat policy is
    registered to floor: the leftover is not spent and that is stated, not an error."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=100, seed=0)
    assert r.n_pipelines == 2
    assert r.evaluations_spent == 96


def test_an_exact_tie_keeps_the_earlier_pipeline():
    """Registered convention (Q52 §2 amended). Deciding an exact tie by recency would
    make the reported answer depend on float equality between independent runs."""
    inst, oracle, bounds = _cell()
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0,
                       _confirmation_override=(0.5, 0.5, 0.5, 0.5))
    assert r.chosen_pipeline[192] == 0


def test_explicit_seeds_are_used_verbatim_rather_than_derived_by_increment():
    """The registration fixes repeat seeds as H(instance_id, 7000 + repeat_index), so
    the arm must accept them rather than deriving seed+i from a single scalar."""
    inst, oracle, bounds = _cell()
    wanted = (11, 22, 33, 44)
    r = run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0,
                       seeds=wanted)
    assert r.seeds == wanted


def test_explicit_seeds_shorter_than_the_cap_allows_are_refused():
    inst, oracle, bounds = _cell()
    with pytest.raises(ValueError):
        run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=200, seed=0,
                       seeds=(1, 2))


def test_a_negative_cap_is_refused():
    inst, oracle, bounds = _cell()
    with pytest.raises(ValueError):
        run_doe_repeat(oracle, bounds, truth=oracle.truth,
                       optimum_value=float(inst.optimum_value), cap=-1, seed=0)
