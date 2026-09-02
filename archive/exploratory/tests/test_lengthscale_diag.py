"""Helpers for the lengthscale diagnostic.

DIAGNOSTIC ONLY. Nothing here touches an E2 number, an arm, or a config. The
question it exists to answer is whether the GP's fitted lengthscales at d=6 sit
near BoTorch's dimension-scaled prior median (~10 on a unit domain), which would
make the primary-cell loss partly a configuration artefact, or materially below
it, which would leave the nuisance-dimension reading standing.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from boec.lengthscale_diag import (
    censored_fwhm,
    fraction_at_floor,
    prior_band_fraction,
    prior_loc_scale,
    prior_mode,
)
from boec.oracles import HillOracle, load_ensemble
from boec.surrogate import build_gp


def _unfitted(d: int):
    b = torch.stack([torch.zeros(d, dtype=torch.double),
                     torch.ones(d, dtype=torch.double)])
    X = torch.rand(2 * d + 2, d, dtype=torch.double)
    Y = torch.rand(2 * d + 2, 1, dtype=torch.double)
    V = torch.full((2 * d + 2, 1), 0.01, dtype=torch.double)
    return build_gp(X, Y, V, b, fit=False)


@pytest.mark.parametrize("d", [6, 8])
def test_prior_is_the_dimension_scaled_one_the_diagnostic_assumes(d):
    """The whole diagnostic rests on loc = sqrt(2) + 0.5*log(d). Read it live.

    Asserted against the installed library rather than a docstring, because the
    entire question -- is a prior median of ~10 on a unit domain dominating the
    fit -- is void if the installed version uses different numbers.
    """
    loc, scale = prior_loc_scale(_unfitted(d))
    assert loc == pytest.approx(math.sqrt(2) + 0.5 * math.log(d), abs=1e-4)
    assert scale == pytest.approx(math.sqrt(3), abs=1e-4)
    assert math.exp(loc) > 10.0          # ten times the domain width, at both d


@pytest.mark.parametrize("d", [6, 8])
def test_prior_mode_is_where_a_signal_free_fit_actually_lands(d):
    """THE CORRECTION. The fit is MAP, so its no-data attractor is the prior MODE.

    An earlier version of this module anchored its decision rule on the prior
    MEDIAN, exp(loc) = 10.08 at d=6, and read "lengthscales far below 10" as
    evidence the data had won. It is not: `fit_gpytorch_mll` maximises the
    marginal log likelihood PLUS the log prior, the constraint carries
    `transform=None` so raw and constrained lengthscales coincide, and the
    argmax of the prior term alone is exp(loc - scale**2) = 0.5016 -- which is
    also the value gpytorch initialises the kernel to. A fit that has learned
    NOTHING sits there, and the old rule scored that as maximal learning.

    This test is the guard: it asserts the mode formula against the value the
    library actually initialises to, so the anchor cannot drift back.
    """
    model = _unfitted(d)
    loc, scale = prior_loc_scale(model)
    mode = prior_mode(model)

    assert mode == pytest.approx(math.exp(loc - scale**2), rel=1e-9)
    assert mode < 1.0 < math.exp(loc)          # mode below the box, median 10x above it
    # gpytorch initialises the kernel AT the mode -- unfitted, this is what you get
    from boec.surrogate import lengthscales as _ls
    assert float(_ls(model).detach().ravel()[0]) == pytest.approx(mode, rel=1e-4)


def test_prior_band_fraction_is_a_prior_mass_statistic_not_a_dominance_one():
    """Kept, but only as what it is: where a value sits in the prior's bulk.

    It must NOT be read as prior dominance. The band around the median excludes
    the mode entirely, so a completely uninformed fit scores 0.0 on it.
    """
    loc, scale = math.log(10.0), 1.0
    ls = np.array([10.0, 10.0 * math.e**0.5, 10.0 * math.e**2.0, 0.1])
    assert prior_band_fraction(ls, loc, scale) == pytest.approx(0.5)

    # the decisive case: the MAP attractor is outside its own prior's band
    loc, scale = 2.3101, math.sqrt(3)
    assert prior_band_fraction(np.array([math.exp(loc - scale**2)]), loc, scale) == 0.0


def test_fraction_at_floor_flags_only_lengthscales_pinned_to_the_constraint():
    lb = 0.025
    ls = np.array([0.025, 0.0250001, 0.03, 1.0])
    assert fraction_at_floor(ls, lb) == pytest.approx(0.5)
    assert fraction_at_floor(np.array([1.0, 2.0]), lb) == 0.0


def test_fraction_at_floor_refuses_a_configuration_with_no_floor():
    """The Gamma-prior kernel installs Positive(), lower bound 0.0.

    Returning 0.0 there would read as "nothing is pinned" when in fact there is
    nothing to pin against -- a silent wrong answer on the exact configuration a
    sensitivity analysis would use.
    """
    with pytest.raises(ValueError, match="no lower bound"):
        fraction_at_floor(np.array([1.0, 2.0]), 0.0)


def test_censored_fwhm_brackets_the_half_maximum_of_the_true_factor():
    """The true feature scale each fitted lengthscale is measured against.

    Censored at 1.0 on purpose: a factor whose decline is shallow never drops
    back to half-maximum inside the coded box, and the GP only ever sees [0, 1].
    """
    inst = load_ensemble(dim=6)[0]
    orc = HillOracle(inst)
    w = censored_fwhm(inst)

    assert w.shape == (6,)
    assert np.all(w > 0.0) and np.all(w <= 1.0)

    grid = np.linspace(0.0, 1.0, 4001)
    X = np.tile(inst.optimum_x, (grid.size, 1))
    for j in range(6):
        Xj = X.copy()
        Xj[:, j] = grid
        curve = orc.base_factors(Xj)[:, j]
        assert curve.max() == pytest.approx(1.0, abs=1e-6)     # peak-normalised
        # the reported width is the measure of the super-half-maximum set
        assert w[j] == pytest.approx(
            (curve >= 0.5).mean(), abs=2e-3
        )


def test_censored_fwhm_is_narrower_for_a_sharper_hill():
    """Sanity that the number tracks the shape it claims to summarise."""
    import dataclasses

    inst = load_ensemble(dim=6)[0]
    sharp = dataclasses.replace(inst, n_hill=inst.n_hill * 2.0)
    assert np.all(censored_fwhm(sharp) <= censored_fwhm(inst) + 1e-9)
    assert np.any(censored_fwhm(sharp) < censored_fwhm(inst))
