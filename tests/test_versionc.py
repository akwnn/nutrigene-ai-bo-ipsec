"""Version C -- the regime detector, `n_eff`, and the statistics section 3.2 offers.

Registered in `docs/OPEN-QUESTIONS.md`. Section 3.3's protocol is FREEZE THEN SCORE ONCE:
the rule and its threshold are fitted on hill, levy and rosenbrock, frozen in the
registration, and scored exactly once on hartmann6 and ackley. Nothing in this file may
be re-tuned after that scoring; scoring the held-out families more than once is tuning on
the evaluation set, which is the exact failure this project exists to document.
"""

import math

import torch

from boec.versionc import ard_lengthscales, n_effective


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
