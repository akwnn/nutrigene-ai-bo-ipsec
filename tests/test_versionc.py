"""Version C -- the regime detector, `n_eff`, and the statistics section 3.2 offers.

Registered in `docs/OPEN-QUESTIONS.md`. Section 3.3's protocol is FREEZE THEN SCORE ONCE:
the rule and its threshold are fitted on hill, levy and rosenbrock, frozen in the
registration, and scored exactly once on hartmann6 and ackley. Nothing in this file may
be re-tuned after that scoring; scoring the held-out families more than once is tuning on
the evaluation set, which is the exact failure this project exists to document.
"""

import math

import torch

from boec.versionc import ard_lengthscales, conservative_columns, n_effective


def _unit_lengthscales(d: int, value: float = 0.5) -> torch.Tensor:
    return torch.full((d,), value, dtype=torch.double)


def test_n_eff_is_one_when_no_design_point_is_within_a_lengthscale():
    """The floor. `n_eff = 1` says the posterior argmax stands on its own information.

    This is not a corner case: measured neighbour density for a 48-point design in 6D at
    the fitted lengthscale is 0.49 points per lengthscale, so an empty neighbourhood is
    the common case rather than the exception.
    """
    X = torch.tensor([[0.9, 0.9], [0.95, 0.05]], dtype=torch.double)
    x_hat = torch.tensor([0.1, 0.1], dtype=torch.double)
    assert n_effective(X, x_hat, _unit_lengthscales(2, 0.1)) == 1


def test_n_eff_counts_every_point_when_all_are_within_a_lengthscale():
    X = torch.rand(7, 3, generator=torch.Generator().manual_seed(0), dtype=torch.double)
    x_hat = torch.tensor([0.5, 0.5, 0.5], dtype=torch.double)
    assert n_effective(X, x_hat, _unit_lengthscales(3, 100.0)) == 8


def test_the_ard_metric_is_anisotropic_and_the_count_moves_with_it():
    """If the lengthscales did not enter per axis this would be a Euclidean ball, and
    `n_eff` would answer a question about the box rather than about the fitted model."""
    X = torch.tensor([[0.5, 0.9]], dtype=torch.double)
    x_hat = torch.tensor([0.5, 0.5], dtype=torch.double)
    wide_on_x1 = torch.tensor([0.1, 1.0], dtype=torch.double)
    narrow_on_x1 = torch.tensor([1.0, 0.1], dtype=torch.double)
    assert n_effective(X, x_hat, wide_on_x1) == 2
    assert n_effective(X, x_hat, narrow_on_x1) == 1


def test_the_boundary_is_inclusive_at_exactly_one_lengthscale():
    """`<= 1`, as registered. An exclusive bound is a different estimator, and at 0.378
    neighbours per lengthscale a single point either way is a third of the statistic."""
    X = torch.tensor([[0.5 + 0.25, 0.5]], dtype=torch.double)
    x_hat = torch.tensor([0.5, 0.5], dtype=torch.double)
    assert n_effective(X, x_hat, _unit_lengthscales(2, 0.25)) == 2


def test_a_design_point_sitting_exactly_on_x_hat_is_counted_and_so_is_the_plus_one():
    """The registered formula is `1 + |{x_i : d_ARD <= 1}|` and it is implemented
    literally, including here, where the two terms describe the same well.

    `x_hat` is the argmax of a posterior mean and is generically not a design point, so
    this costs nothing in practice -- but the double count is a property of the
    registration rather than of this implementation, and hiding it behind a special case
    would make the shipped number differ from the registered one.
    """
    X = torch.tensor([[0.4, 0.4]], dtype=torch.double)
    x_hat = torch.tensor([0.4, 0.4], dtype=torch.double)
    assert n_effective(X, x_hat, _unit_lengthscales(2, 0.3)) == 2


def test_a_lengthscale_of_the_wrong_width_raises():
    X = torch.rand(4, 3, generator=torch.Generator().manual_seed(1), dtype=torch.double)
    x_hat = torch.zeros(3, dtype=torch.double)
    try:
        n_effective(X, x_hat, _unit_lengthscales(2))
    except ValueError as e:
        assert "lengthscale" in str(e).lower()
    else:
        raise AssertionError("a d-mismatched lengthscale vector must raise")


def test_ard_lengthscales_reads_the_fitted_vector_off_a_real_gp():
    """Read off the live model, never hardcoded -- the same rule
    `boec.lse.exclusion_radius` follows, and for the same reason: a fixed width means
    something different at every noise level and dimension."""
    from boec.optimizers import lhs_design
    from boec.replay import unit_bounds
    from boec.surrogate import build_gp

    d = 3
    bounds = unit_bounds(d)
    X = lhs_design(bounds, 20, seed=0)
    Y = (1.0 - (X - 0.5).pow(2).sum(dim=1, keepdim=True)).double()
    Yvar = torch.full_like(Y, 1e-4)
    ls = ard_lengthscales(build_gp(X, Y, Yvar, bounds))
    assert ls.shape == (d,)
    assert bool((ls > 0).all())


def test_n_eff_falls_as_the_fitted_lengthscale_shrinks_on_a_real_design():
    """The behaviour section 2.2's allocation rule depends on: `n_eff` is a statement
    about how much local information the plate bought, so it must fall as the model's
    own notion of 'local' tightens."""
    from boec.optimizers import lhs_design
    from boec.replay import unit_bounds

    X = lhs_design(unit_bounds(6), 40, seed=0)
    x_hat = torch.full((6,), 0.5, dtype=torch.double)
    counts = [n_effective(X, x_hat, _unit_lengthscales(6, v))
              for v in (0.1, 0.3, 0.6, 1.0, 5.0)]
    assert counts == sorted(counts), f"n_eff must be monotone in lengthscale, got {counts}"
    assert counts[0] == 1 and counts[-1] == 41


# ---------------------------------------------------------------------------
# Version C sections 1.2 and 1.3 -- the conservative-set columns.
#
# `versionb.json` and `k6b-conservative*.json` carry `ce_vol` but no false-inclusion
# rate and no prevalence, so `boec.calibration.error_volumes` cannot be computed on a
# conservative set at all. That is the absence section 1.3 names, and it is the same
# path section 1.2's cross-fit re-score has to write.
# ---------------------------------------------------------------------------


def _corr_draws(n_draws, n_pts=80, seed=0, shift=0.0):
    g = torch.Generator().manual_seed(seed)
    base = torch.linspace(0.55, 0.75, n_pts, dtype=torch.double) + shift
    return (base.unsqueeze(0)
            + 0.12 * torch.randn(n_draws, 1, generator=g, dtype=torch.double)
            + 0.02 * torch.randn(n_draws, n_pts, generator=g, dtype=torch.double))


def _sel_val(n_pts=80, seed=0):
    """Two blocks of 512 drawn SEQUENTIALLY from one generator -- the only construction
    that leaves the committed first half bit-identical. Measured: `randn(n, 1024)[:, :512]`
    is NOT `randn(n, 512)`, because torch fills in memory order, so drawing 1,024 at once
    would silently change every committed `ce_*` column."""
    g = torch.Generator().manual_seed(seed)
    base = torch.linspace(0.55, 0.75, n_pts, dtype=torch.double)
    blocks = []
    for _ in range(2):
        blocks.append(base.unsqueeze(0)
                      + 0.12 * torch.randn(512, 1, generator=g, dtype=torch.double)
                      + 0.02 * torch.randn(512, n_pts, generator=g, dtype=torch.double))
    return blocks


def test_conservative_columns_reproduce_the_committed_keys_exactly():
    """The committed `ce_vol` / `ce_empty` / `ce_contain` / `ce_empirical` must come back
    bit-identical, or the re-score is a new estimand rather than an added column."""
    from boec.vorobev import (conservative_estimate, containment_probability,
                              empirical_containment)

    sel, val = _sel_val()
    truth = torch.linspace(0.4, 0.8, 80, dtype=torch.double)
    cols = conservative_columns(sel, val, truth, theta=0.5, alphas=(0.50, 0.95))

    for a in (0.50, 0.95):
        ce = conservative_estimate(sel, 0.5, a)
        n_ce = int(ce.sum())
        assert cols[f"ce_vol_{a}"] == n_ce / ce.numel()
        assert cols[f"ce_empty_{a}"] == (n_ce == 0)
        assert cols[f"ce_contain_{a}"] == (containment_probability(sel, ce, 0.5)
                                           if n_ce else float("nan")) or n_ce == 0
        emp = empirical_containment(ce, truth, 0.5)
        assert cols[f"ce_empirical_{a}"] == (float("nan") if emp is None else float(emp)) \
            or emp is None


def test_conservative_columns_add_the_prevalence_and_the_false_inclusion_rate():
    """The two absences. Without both, `error_volumes` is not computable on a
    conservative set -- which has blocked the primary error-volume metric twice."""
    from boec.calibration import error_volumes

    sel, val = _sel_val()
    truth = torch.linspace(0.4, 0.8, 80, dtype=torch.double)
    cols = conservative_columns(sel, val, truth, theta=0.5, alphas=(0.50,))

    assert "true_frac_above_tau" in cols
    assert "ce_fi_0.5" in cols
    ev = error_volumes(cols["ce_vol_0.5"], cols["ce_fi_0.5"], cols["true_frac_above_tau"])
    assert math.isfinite(ev["total_error_vol"])
    assert cols["ce_type_I_vol_0.5"] == ev["type_I_vol"]
    assert cols["ce_total_error_vol_0.5"] == ev["total_error_vol"]


def test_the_split_column_is_scored_on_the_validation_half():
    from boec.vorobev import conservative_estimate_split

    sel, val = _sel_val()
    truth = torch.linspace(0.4, 0.8, 80, dtype=torch.double)
    cols = conservative_columns(sel, val, truth, theta=0.5, alphas=(0.95,))
    _, expected = conservative_estimate_split(torch.cat([sel, val]), 0.5, 0.95)
    assert cols["ce_split_contain_0.95"] == expected or math.isnan(expected)


def test_the_split_column_sits_beside_the_circular_one_and_never_replaces_it():
    """Both are reported. Removing the circular column would hide the tautology rather
    than expose it, and the difference between the two IS the selection bias."""
    sel, val = _sel_val()
    truth = torch.linspace(0.4, 0.8, 80, dtype=torch.double)
    cols = conservative_columns(sel, val, truth, theta=0.5, alphas=(0.95,))
    assert "ce_contain_0.95" in cols and "ce_split_contain_0.95" in cols


def test_mismatched_half_sizes_raise():
    sel, val = _sel_val()
    try:
        conservative_columns(sel, val[:100], torch.zeros(80, dtype=torch.double),
                             theta=0.5, alphas=(0.95,))
    except ValueError as e:
        assert "half" in str(e).lower() or "equal" in str(e).lower()
    else:
        raise AssertionError("unequal halves must raise, not silently re-weight")
