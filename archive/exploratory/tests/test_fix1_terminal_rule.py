"""Fix 1's terminal rule: screen the registered grid, then polish with the shared locator.

Registered in `docs/OPEN-QUESTIONS.md` (commit 4e14769) **before**
`scripts/run_fix1_terminal_rule.py` existed.

The contract that matters is T1.4c's, and this project has already shipped one violation of
it: a rule that scores each method "at the point its model recommends" is a comparison of
MODELS only if the recommendation is *located* identically for every arm. Q29's BO arm once
screened at `num_restarts=10, raw_samples=256` **unseeded** while its DoE arm screened at
`20 / 4096` seeded — a 16x asymmetry pointing at whichever arm got the bigger screen (see
`tests/test_q29_locator.py`). Fix 1 therefore locates every arm with **one** function at
**one** setting, and these tests pin the properties that make that claim true:

* the rule never returns a point worse than its own screen, so adding the polish cannot
  make an arm look worse than the grid alone would have;
* it is deterministic under its seed;
* the grid point survives in the result, so the polish's contribution is measurable rather
  than assumed.

The grid values are passed IN, never recomputed here. `model.posterior` over a
20,000-point grid builds the joint covariance: 100.6 s against 0.06 s at 2,000 points
(`boec.designspace.gp_adapter`). A locator that quietly re-evaluated the grid would put
that trap back.
"""

from __future__ import annotations

import pytest
import torch

from boec.metrics import grid_screened_argmax

BOX6 = torch.stack([torch.zeros(6, dtype=torch.double),
                    torch.ones(6, dtype=torch.double)])


def _quadratic(centre: torch.Tensor):
    """Smooth, single-peaked, maximum at ``centre``. Off any coarse grid on purpose."""
    def predict(Z: torch.Tensor) -> torch.Tensor:
        return -((Z.double() - centre) ** 2).sum(-1, keepdim=True)
    return predict


def test_polish_beats_a_coarse_screen_on_a_smooth_maximum():
    centre = torch.full((6,), 0.4123456789, dtype=torch.double)
    predict = _quadratic(centre)
    grid = torch.rand(256, 6, generator=torch.Generator().manual_seed(1),
                      dtype=torch.double)
    values = predict(grid).reshape(-1)

    r = grid_screened_argmax(predict, grid, values, BOX6, seed=0)

    assert not r.from_grid, "a coarse random screen should not beat L-BFGS-B here"
    assert r.value > r.value_grid
    assert torch.allclose(r.x, centre, atol=1e-4), r.x


def test_never_returns_a_point_worse_than_its_own_screen():
    """The polish is allowed to fail. It is not allowed to lose ground.

    A needle at one grid point that the polish's 4,096-point Sobol screen cannot see,
    beside a broad bump the polish will happily climb. The grid must win.
    """
    grid = torch.rand(512, 6, generator=torch.Generator().manual_seed(2),
                      dtype=torch.double)
    needle = grid[7].clone()
    bump = torch.full((6,), 0.8, dtype=torch.double)

    def predict(Z: torch.Tensor) -> torch.Tensor:
        Z = Z.double()
        spike = 10.0 * torch.exp(-((Z - needle) ** 2).sum(-1) / 1e-8)
        broad = torch.exp(-((Z - bump) ** 2).sum(-1) / 0.5)
        return (spike + broad).unsqueeze(-1)

    values = predict(grid).reshape(-1)
    r = grid_screened_argmax(predict, grid, values, BOX6, seed=0)

    assert r.from_grid, "the screen found a better point and must have been kept"
    assert r.value == r.value_grid
    assert torch.allclose(r.x, needle)
    assert r.value >= float(values.max())


def test_deterministic_under_its_seed():
    predict = _quadratic(torch.full((6,), 0.37, dtype=torch.double))
    grid = torch.rand(128, 6, generator=torch.Generator().manual_seed(3),
                      dtype=torch.double)
    values = predict(grid).reshape(-1)
    a = grid_screened_argmax(predict, grid, values, BOX6, seed=5)
    b = grid_screened_argmax(predict, grid, values, BOX6, seed=5)
    assert torch.equal(a.x, b.x) and a.value == b.value


def test_the_screened_point_survives_beside_the_chosen_one():
    """Fix 1 reports the grid-only regret beside the combined one; it needs both points."""
    predict = _quadratic(torch.full((6,), 0.6, dtype=torch.double))
    grid = torch.rand(64, 6, generator=torch.Generator().manual_seed(4),
                      dtype=torch.double)
    values = predict(grid).reshape(-1)
    r = grid_screened_argmax(predict, grid, values, BOX6, seed=0)

    assert r.x_grid.shape == (6,)
    assert r.value_grid == pytest.approx(float(values.max()))
    assert torch.allclose(r.x_grid, grid[int(torch.argmax(values))])


def test_mismatched_grid_values_raise_rather_than_indexing_the_wrong_row():
    """Silently pairing a grid with someone else's values is a wrong answer, not an error."""
    predict = _quadratic(torch.full((6,), 0.5, dtype=torch.double))
    grid = torch.rand(32, 6, generator=torch.Generator().manual_seed(5),
                      dtype=torch.double)
    with pytest.raises(ValueError, match="one value per grid row"):
        grid_screened_argmax(predict, grid, predict(grid).reshape(-1)[:31], BOX6, seed=0)
