"""Oracle correctness. Every claim the downstream numbers rest on."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.designs import central_composite, screening_design, scale_to_box, sub_box_bounds
from boec.rsm import fit_second_order, second_order_design_matrix
from boec.evaluators import SyntheticEvaluator
from boec.oracles import (
    Ackley,
    Branin,
    Hartmann6,
    HillOracle,
    SamplerConfig,
    accept_instance,
    delta_max,
    delta_supremum,
    depth_of_r,
    factor_value,
    generate_ensemble,
    invert_r,
    propose_instance,
)
from boec.space import MetricIdentity, SearchSpace

RNG = np.random.default_rng(20260807)


# --------------------------------------------------------------------------- factor
def test_peak_normalisation_is_exactly_one():
    """max_x ft(x) == 1. Without it, peak heights span 2.7x and equal weights lie."""
    grid = np.linspace(1e-9, 1.0, 200_001)
    worst = 0.0
    for _ in range(200):
        xs, n, r = RNG.uniform(0.1, 0.95), RNG.uniform(1, 3), RNG.uniform(1.05, 8)
        v = factor_value(grid, np.array(xs), np.array(n), np.array(r))
        worst = max(worst, abs(v.max() - 1.0))
    assert worst < 1e-8, worst


def test_xstar_is_the_exact_argmax():
    """xstar = sqrt(EC50*IC50), exactly, by construction."""
    grid = np.linspace(1e-9, 1.0, 200_001)
    worst = 0.0
    for _ in range(200):
        xs, n, r = RNG.uniform(0.1, 0.95), RNG.uniform(1, 3), RNG.uniform(1.05, 8)
        v = factor_value(grid, np.array(xs), np.array(n), np.array(r))
        worst = max(worst, abs(grid[int(v.argmax())] - xs))
    assert worst < 1e-4, worst


# ------------------------------------------------------------------------ inversion
def test_inversion_verification_case():
    """(xstar=0.4, n=2, delta=0.414) -> s = 3.9917 -> r = 4."""
    r = float(invert_r(0.4, 2.0, 0.414))
    assert r == pytest.approx(3.9917, abs=5e-4)


def test_inversion_round_trip():
    """delta(invert_r(delta)) == delta over the sampled region."""
    for _ in range(500):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1, 3)
        dmax = float(delta_max(xs, n))
        delta = RNG.uniform(0.3, 0.9) * dmax
        r = float(invert_r(xs, n, delta))
        assert np.isfinite(r) and r > 1.0
        assert float(depth_of_r(xs, n, r)) == pytest.approx(delta, abs=1e-9)


def test_inversion_takes_the_root_above_one():
    """The quadratic's roots multiply to 1; we must return the one exceeding 1."""
    for _ in range(300):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1, 3)
        delta = RNG.uniform(0.3, 0.9) * float(delta_max(xs, n))
        r = float(invert_r(xs, n, delta))
        s = r ** (n / 2.0)
        assert s > 1.0
        assert s * (1.0 / s) == pytest.approx(1.0)


def test_delta_max_closed_form_equals_brute_force_scan():
    """The spec's '1-D scan over r in [2,8] maximising delta' is a no-op.

    delta is strictly decreasing in r, so the maximum is always at r = r_min.
    """
    rs = np.linspace(2.0, 8.0, 400)
    for _ in range(200):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1, 3)
        scanned = float(np.max(depth_of_r(xs, n, rs)))
        assert float(delta_max(xs, n)) == pytest.approx(scanned, abs=1e-12)
        # and monotone decreasing, which is why the scan is redundant
        assert np.all(np.diff(depth_of_r(xs, n, rs)) <= 1e-12)


def test_delta_supremum_bounds_feasibility():
    """delta <= ((V-1)/(V+1))^2 with V = xstar^-n; beyond it no real root exists."""
    for _ in range(500):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1, 3)
        sup = float(delta_supremum(xs, n))
        assert np.isfinite(invert_r(xs, n, sup * 0.999))
        assert not np.isfinite(invert_r(xs, n, min(sup * 1.001 + 1e-6, 0.999999)))


# ------------------------------------------------------------------------- sampling
def test_sampled_delta_never_exceeds_delta_max():
    cfg = SamplerConfig()
    for seed in range(60):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        assert np.all(inst.delta <= inst.delta_max_achieved + 1e-12)


def test_r_cap_is_enforced():
    """Left unenforced the inversion exceeds r_cap in ~31% of draws (max seen 50)."""
    cfg = SamplerConfig()
    for seed in range(80):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        assert np.all(inst.r <= cfg.r_cap + 1e-12)
        assert np.all(inst.r >= cfg.r_min - 1e-12)


def test_oracle_version_covers_acceptance_parameters():
    """Rejections consume RNG draws, so the acceptance rule is part of the identity."""
    base = SamplerConfig()
    assert base.version() != SamplerConfig(accept_floor=0.050).version()
    assert base.version() != SamplerConfig(formula_prefloor=0.080).version()
    assert base.version() != SamplerConfig(gamma_max=0.5).version()
    assert base.version() != SamplerConfig(accept_on="formula").version()
    assert base.version() == SamplerConfig().version()


def test_instance_id_depends_on_version():
    cfg_a, cfg_b = SamplerConfig(), SamplerConfig(accept_floor=0.050)
    a = propose_instance(6, 0, cfg_a)
    b = propose_instance(6, 0, cfg_b)
    assert a is not None and b is not None
    assert a.instance_id != b.instance_id


# --------------------------------------------------------------- interaction modes
def test_product_interaction_cannot_move_the_optimum():
    """The v6 bug, asserted so it stays fixed.

    df/dx_i = ft_i'(x_i) * [w_i + (1/k) sum_j beta_ij ft_j(x_j)] -- no x_i in the
    bracket, so the joint optimum is the vector of per-factor peaks whenever the
    bracket is positive, and the 'non-separability' acceptance check can never pass.
    """
    cfg = SamplerConfig(interaction="product")
    checked = 0
    for seed in range(40):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        assert inst.beta is not None
        bracket = inst.weights.copy()
        for (i, j), b in zip(inst.pairs, inst.beta):
            bracket[i] += b / inst.k_pairs
            bracket[j] += b / inst.k_pairs
        if np.any(bracket <= 0):
            continue  # the pathological 8%: optimum jumps to a box edge
        xopt, _ = HillOracle(inst).locate_optimum(n_restarts=25, seed=seed)
        assert np.abs(xopt - inst.xstar).max() < 1e-4
        checked += 1
    assert checked >= 10


def test_peak_modulation_moves_the_optimum_off_the_closed_form():
    cfg = SamplerConfig(interaction="peak_modulation", gamma_max=1.0)
    shifts = []
    for seed in range(40):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        shifts.append(np.abs(HillOracle(inst).fixed_point_optimum() - inst.xstar).max())
    assert len(shifts) >= 20
    assert np.median(shifts) > 0.01, np.median(shifts)


def test_gamma_zero_reduces_to_the_separable_case():
    cfg = SamplerConfig(interaction="peak_modulation", gamma_max=0.0)
    inst = propose_instance(6, 3, cfg)
    assert inst is not None
    assert np.abs(HillOracle(inst).fixed_point_optimum() - inst.xstar).max() < 1e-12


def test_fixed_point_optimum_has_value_exactly_one():
    """At the fixed point every factor sits at its own peak, so f = sum w_i = 1."""
    cfg = SamplerConfig(interaction="peak_modulation")
    checked = 0
    for seed in range(30):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        o = HillOracle(inst)
        v = float(o.f(o.fixed_point_optimum()[None, :])[0])
        assert v == pytest.approx(1.0, abs=1e-12), v
        checked += 1
    assert checked >= 15


def test_fixed_point_agrees_with_multistart_search():
    cfg = SamplerConfig(interaction="peak_modulation")
    for seed in range(12):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        o = HillOracle(inst)
        _, v = o.locate_optimum(n_restarts=30, seed=seed)
        assert v <= 1.0 + 1e-9
        assert v == pytest.approx(1.0, abs=1e-6)


def test_positivity_is_automatic_under_peak_modulation():
    cfg = SamplerConfig(interaction="peak_modulation")
    for seed in range(20):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        probe = RNG.uniform(0, 1, (3000, 6))
        assert float(HillOracle(inst).f(probe).min()) >= 0.0


# ------------------------------------------------------------------------ acceptance
def test_accepted_instances_clear_the_true_depth_floor():
    cfg = SamplerConfig()
    insts, audit = generate_ensemble(6, 5, cfg, seed0=100)
    assert len(insts) == 5, audit
    for inst in insts:
        assert inst.true_depth is not None
        assert inst.true_depth >= cfg.accept_floor
        assert inst.optimum_value == pytest.approx(1.0, abs=1e-9)


def test_acceptance_is_noise_independent():
    """The floor is frozen at the primary noise level; one ensemble serves both.

    A sigma_rel-dependent criterion would change the ensemble with the noise level,
    mixing a noise effect with an ensemble effect in the 0.10-vs-0.25 comparison.
    Nothing in SamplerConfig references sigma_rel -- this asserts it stays that way.
    """
    assert not any("sigma" in f for f in SamplerConfig.__dataclass_fields__)
    a, _ = generate_ensemble(6, 3, SamplerConfig(), seed0=7)
    b, _ = generate_ensemble(6, 3, SamplerConfig(), seed0=7)
    for x, y in zip(a, b):
        assert x.instance_id == y.instance_id
        assert np.allclose(x.xstar, y.xstar)


def test_formula_depth_overstates_true_depth_under_interaction():
    """Why acceptance moved to the numerical depth: the closed form is optimistic."""
    cfg = SamplerConfig(interaction="product", accept_on="formula")
    ratios = []
    for seed in range(25):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        _ok, diag = accept_instance(inst, cfg)
        if "true_depth" not in diag:
            continue
        ratios.append(diag["true_depth"] / diag["formula_depth"])
    assert len(ratios) >= 8
    assert np.median(ratios) < 0.95, np.median(ratios)


# ------------------------------------------------------------------------ evaluator
def _simple_oracle():
    cfg = SamplerConfig()
    inst = propose_instance(6, 0, cfg)
    assert inst is not None
    return HillOracle(inst)


def test_evaluator_shapes_are_n_by_m():
    ev = SyntheticEvaluator(_simple_oracle(), MetricIdentity("y", "au", "v1"))
    Y, Yvar = ev.evaluate(RNG.uniform(0, 1, (7, 6)))
    assert Y.shape == (7, 1) and Yvar.shape == (7, 1)
    assert ev.n_evaluations == 7


def test_evaluator_does_not_expose_y_true():
    """The regret story depends on this."""
    assert not hasattr(SyntheticEvaluator, "evaluate_true__public")
    from boec.evaluators import Evaluator

    assert not hasattr(Evaluator, "evaluate_true")
    assert "evaluate_true" not in Evaluator.__abstractmethods__


def test_yvar_is_variance_not_sd_and_in_raw_units():
    """The classic fixed-noise GP bug, and its separate sibling."""
    o = _simple_oracle()
    ev = SyntheticEvaluator(o, MetricIdentity("y", "au", "v1"), sigma_rel=0.1, sigma_add=0.01)
    Y, Yvar = ev.evaluate(RNG.uniform(0, 1, (500, 6)))
    expected = Y**2 * 0.1**2 + 0.01**2
    assert np.allclose(Yvar, expected)
    assert np.all(Yvar > 0)
    # variance, not sd: for |y| ~ 0.5 the variance is ~2.5e-3, the sd ~5e-2
    assert Yvar.mean() < 0.05


def test_oracle_noise_matches_analytic_variance():
    """Empirical variance of repeated evaluate() matches f^2*sig_rel^2 + sig_add^2."""
    o = _simple_oracle()
    x = np.full((1, 6), 0.4)
    ev = SyntheticEvaluator(o, MetricIdentity("y", "au", "v1"), sigma_rel=0.1, sigma_add=0.01)
    draws = np.array([ev.evaluate(x)[0][0, 0] for _ in range(20000)])
    f = float(o.f(x)[0])
    analytic = f**2 * 0.1**2 + 0.01**2
    assert draws.var() == pytest.approx(analytic, rel=0.08)
    assert draws.mean() == pytest.approx(f, rel=0.02)


def test_plugin_yvar_bias_is_the_predicted_one_percent():
    """E[y^2] = f^2(1+sig^2) + sig_add^2, so the plug-in runs ~1% high at sig=0.10."""
    o = _simple_oracle()
    x = np.full((1, 6), 0.4)
    ev = SyntheticEvaluator(o, MetricIdentity("y", "au", "v1"), sigma_rel=0.1, sigma_add=0.01)
    plug = np.array([ev.evaluate(x)[1][0, 0] for _ in range(20000)]).mean()
    f = float(o.f(x)[0])
    analytic = f**2 * 0.1**2 + 0.01**2
    assert 1.0 < plug / analytic < 1.03


def test_analytic_yvar_ablation_leaks_f_and_is_not_the_default():
    o = _simple_oracle()
    md = MetricIdentity("y", "au", "v1")
    assert SyntheticEvaluator(o, md).yvar_mode == "plugin"
    ev = SyntheticEvaluator(o, md, yvar_mode="analytic", sigma_rel=0.1, sigma_add=0.01)
    x = RNG.uniform(0, 1, (50, 6))
    _, Yvar = ev.evaluate(x)
    recovered = np.sqrt(np.maximum(Yvar - 0.01**2, 0)) / 0.1
    assert np.allclose(recovered.ravel(), o.f(x), atol=1e-9)


# -------------------------------------------------------------------------- designs
# Four design tests that lived here were dropped in the port, not lost: B's
# `tests/test_designs.py` already asserts each of them, and A/B agreement depends on
# there being one copy of a claim as much as one copy of a function. The mapping, so
# the deletions are auditable --
#     test_e4_subbox_design_is_48_runs_and_full_rank
#         -> test_e4_design_is_exactly_48_runs + test_e4_design_supports_a_second_order_fit
#     test_coding_round_trips
#         -> test_scale_maps_minus_one_to_lower_and_plus_one_to_upper
#     test_subbox_design_stays_inside_the_subbox
#         -> test_sub_box_stops_short_of_the_peak + test_face_centred_axial_points_stay_inside_the_cube
#     test_rotatable_ccd_escapes_the_subbox
#         -> test_rotatable_axial_points_fall_outside_the_sub_box
# The two below survive because they assert A-side requirements (E2's budget, and the
# scorer identity), not design mechanics -- but they now run against B's module.


@pytest.mark.xfail(
    strict=True,
    reason="BLOCKED ON B, see OPEN-QUESTIONS Q14. `screening_design(6)` returns 36 runs "
    "(2^(6-1) + 4) because `_GENERATORS` has no (6, 2) entry, so it cannot build the "
    "16-run 2^(6-2) resolution-IV fraction E2's budget needs. 36 + 27 = 63 blows the "
    "48-run budget and would make the DoE arm incomparable to every other arm. "
    "designs.py is B's under Q2 and it deliberately refuses to invent generators, so "
    "A is not adding one. strict=True so this fails loudly the moment B fixes it.",
)
def test_doe_arm_budget_is_47_design_runs_plus_one_confirmation():
    """E2's sequential-DoE arm must spend exactly the same 48 as every other arm.

    20 + 27 design runs + 1 confirmation. Stage 4 (evaluating the predicted optimum)
    is not optional: without it the arm's best-so-far is just its best design point
    and the pipeline's actual output never enters the regret curve.
    """
    stage1 = screening_design(6, n_centre=4, n_derived=2)
    assert stage1.points.shape == (20, 6)          # 2^(6-2) resolution IV + 4 centre
    stage2 = central_composite(4, n_centre=3, n_derived=0, face_centred=True)
    assert stage2.points.shape == (27, 4)          # 16 + 8 + 3
    assert len(stage1.points) + len(stage2.points) == 47

    M = second_order_design_matrix(stage2.points)
    assert M.shape[1] == 15                        # 1 + 4 + 4 + 6 terms at d=4
    assert np.linalg.matrix_rank(M) == 15


def test_second_order_pi_width_is_rank_identical_to_leverage():
    """The 'DoE comparator' scorer IS hat-matrix leverage; report one, not two.

    E4 scores candidates by `second_order_pi_width`. For a fixed fit, `t` and
    `sigma_hat` are constants and `sqrt(1 + h)` is strictly increasing, so ranking by
    interval width and ranking by leverage are the *same* ranking. Two of E4's three
    scorers would otherwise be reported as independent evidence when one is a
    monotone relabelling of the other.

    Asserted against B's own `prediction_interval_width`, not a local reimplementation,
    so the identity is checked on the function E4 actually calls.
    """
    from scipy.stats import spearmanr

    x_star = torch.full((6,), 0.40, dtype=torch.double)
    sub = sub_box_bounds(x_star, 0.8)
    design = central_composite(6, n_centre=4, n_derived=1, face_centred=True)
    train_X = scale_to_box(design.coded, sub)
    train_Y = torch.from_numpy(RNG.uniform(0, 1, (train_X.shape[0], 1)))
    fit = fit_second_order(train_X, train_Y)

    Q = torch.from_numpy(RNG.uniform(0, 1, (2000, 6)))
    width = fit.prediction_interval_width(Q).flatten().numpy()

    M = np.asarray(second_order_design_matrix(train_X), dtype=float)
    XtXi = np.linalg.pinv(M.T @ M)
    Mq = np.asarray(second_order_design_matrix(Q), dtype=float)
    lev = np.einsum("ij,jk,ik->i", Mq, XtXi, Mq)

    assert spearmanr(width, lev).statistic == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------- test functions
def test_standard_test_functions_hit_their_known_optima():
    for oracle in (Branin(), Hartmann6(), Ackley(dim=6)):
        xopt = oracle.optimum_x
        assert xopt is not None
        got = float(oracle.f(xopt[None, :])[0])
        assert got == pytest.approx(oracle.optimum_value, abs=1e-3), oracle.name
        probe = RNG.uniform(0, 1, (20000, oracle.dim))
        assert oracle.f(probe).max() <= got + 1e-6, oracle.name


def test_oracles_share_one_interface():
    """The contract test: the campaign loop must not care which oracle it holds."""
    cfg = SamplerConfig()
    inst = propose_instance(6, 0, cfg)
    assert inst is not None
    md = MetricIdentity("y", "au", "v1")
    for oracle in (Branin(), Hartmann6(), Ackley(dim=6), HillOracle(inst)):
        space = SearchSpace.unit_cube(oracle.dim)
        X = RNG.uniform(0, 1, (5, oracle.dim))
        space.validate(X)
        Y, Yvar = SyntheticEvaluator(oracle, md).evaluate(X)
        assert Y.shape == (5, 1) and Yvar.shape == (5, 1)


def test_shape_violations_fail_loudly():
    o = Hartmann6()
    with pytest.raises(ValueError):
        o.f(RNG.uniform(0, 1, 6))          # (d,) not allowed
    with pytest.raises(ValueError):
        o.f(RNG.uniform(0, 1, (3, 5)))     # wrong d
    with pytest.raises(ValueError):
        SearchSpace.unit_cube(6).validate(np.full((2, 6), 1.5))


# ------------------------------------------------------- v8 active / inert structure
def test_active_mask_has_exactly_n_active_factors_carrying_share():
    cfg = SamplerConfig(n_active=4, active_share=0.90)
    for seed in range(30):
        inst = propose_instance(6, seed, cfg)
        if inst is None:
            continue
        assert inst.active_mask is not None
        assert inst.active_mask.sum() == 4
        assert inst.weights.sum() == pytest.approx(1.0)
        assert inst.weights[inst.active_mask].sum() == pytest.approx(0.90)
        assert inst.weights[~inst.active_mask].sum() == pytest.approx(0.10)


def test_depth_criterion_ignores_inert_coordinates():
    """An inert factor can be pushed to a bound cheaply; that must not cap the depth.

    Including inert faces makes depth = min over ALL i of w_i*delta_i, bounded by 1/d,
    which is precisely what makes sigma_rel=0.25 unreachable at d=8.
    """
    cfg = SamplerConfig(n_active=4, active_share=0.90)
    inst = propose_instance(6, 11, cfg)
    assert inst is not None
    o = HillOracle(inst)
    d_active = o.true_depth(active_only=True)
    d_all = o.true_depth(active_only=False)
    assert d_active > d_all
    assert d_all < 0.05          # an inert face is cheap to reach
    assert d_active > 0.10       # the active subspace is genuinely deep


def test_active_structure_gives_ard_something_to_learn():
    cfg = SamplerConfig(n_active=4, active_share=0.90)
    ratios = []
    for seed in range(30):
        inst = propose_instance(6, seed, cfg)
        if inst is not None:
            ratios.append(inst.influence_ratio)
    assert len(ratios) >= 15
    assert np.median(ratios) >= 4.0, np.median(ratios)


def test_n_active_none_reproduces_flat_weights():
    """n_active=None is the v7 ensemble. Needs v7's prefloor -- 0.120 with flat weights
    demands delta >= 0.72 from every factor, which is why v8 exists."""
    cfg = SamplerConfig(n_active=None, formula_prefloor=0.070)
    inst = propose_instance(6, 5, cfg)
    assert inst is not None
    assert inst.active_mask is not None and inst.active_mask.all()
    assert inst.influence_ratio == 1.0
    assert inst.weights.sum() == pytest.approx(1.0)


def test_flat_weights_cannot_reach_the_sigma_025_floor_at_d8():
    """The v8 justification, asserted: v7 structure is infeasible at the 0.25 floor."""
    target = 3 * 0.25 / np.sqrt(48)
    cfg = SamplerConfig(n_active=None, accept_floor=target, formula_prefloor=0.120)
    insts, _ = generate_ensemble(8, 2, cfg, seed0=300, max_candidates=60)
    assert len(insts) == 0


def test_oracle_version_covers_active_structure():
    base = SamplerConfig()
    assert base.version() != SamplerConfig(n_active=5).version()
    assert base.version() != SamplerConfig(active_share=0.85).version()
    assert base.version() != SamplerConfig(n_active=None).version()


def test_v8_ensemble_clears_the_sigma_025_floor():
    """3*0.25/sqrt(48) = 0.1083. v7 flat weights reach 0% of this at d=8."""
    target = 3 * 0.25 / np.sqrt(48)
    cfg = SamplerConfig(n_active=4, active_share=0.90,
                        accept_floor=target, formula_prefloor=0.120)
    for dim in (6, 8):
        insts, audit = generate_ensemble(dim, 4, cfg, seed0=300, max_candidates=40)
        assert len(insts) == 4, (dim, audit)
        for inst in insts:
            assert inst.true_depth is not None and inst.true_depth >= target
